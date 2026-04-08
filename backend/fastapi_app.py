from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import load_config
from models import AppState
from notion_sync import NotionSyncError, build_end_of_day_payload, sync_end_of_day_to_notion
from runner import (
    build_action_result,
    build_empty_payload_result,
    build_mock_result,
    classify_mission,
)
from storage import ensure_state_file, load_state, save_state


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CONFIG = load_config()


def _process_mission(mission_id: str) -> dict:
    state = load_state()
    mission = next((m for m in state.missions if m.id == mission_id), None)
    if mission is None:
        raise HTTPException(status_code=404, detail="mission not found")

    mission.status = "dispatched"
    classification = classify_mission(mission)
    mission.executionType = classification["execution_type"]
    mission.actionType = classification["action_type"]

    has_payload = any(
        [
            (mission.objective or "").strip(),
            (mission.inputs or "").strip(),
            (mission.expectedOutput or "").strip(),
            (mission.prompt or "").strip(),
        ]
    )
    if not has_payload:
        result = build_empty_payload_result(mission)
        mission.actionStatus = result.get("action_status", "missing_payload")
        mission.actionDetails = result.get("action_details") or None
    elif mission.executionType == "action":
        result = build_action_result(mission, mission.actionType)
        mission.actionStatus = result.get("action_status", "pending_external")
        mission.actionDetails = result.get("action_details") or {
            "action_required": result.get("action_required", False),
            "action_type": result.get("action_type", mission.actionType),
            "action_completed": result.get("action_completed", False),
        }
    else:
        result = build_mock_result(mission)
        mission.actionStatus = ""
        mission.actionDetails = None

    mission.mockResult = result
    mission.resultSummary = result["summary"]
    mission.resultBody = result["full_output"]
    mission.followUp = result["follow_up_needed"]
    mission.carryForward = result["carry_forward"]
    mission.status = "waiting"

    saved = save_state(state)
    saved_mission = next((m for m in saved.missions if m.id == mission_id), None)
    return {
        "ok": True,
        "mission": saved_mission.model_dump(mode="json") if saved_mission else None,
        "result": result,
    }


ensure_state_file()
app = FastAPI(
    title="FieldOps Backend",
    version="0.3.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "fieldops-backend"}


@app.get("/api/state")
def get_state() -> dict:
    return load_state().model_dump(mode="json")


@app.post("/api/state")
def post_state(state: AppState) -> dict:
    saved = save_state(state)
    return {"ok": True, "state": saved.model_dump(mode="json")}


@app.get("/api/notion/end-of-day")
def get_end_of_day(date: str | None = Query(default=None)) -> dict:
    payload = build_end_of_day_payload(load_state(), date_str=date)
    return payload.model_dump(mode="json")


@app.post("/api/notion/end-of-day/sync")
def post_end_of_day_sync(date: str | None = Query(default=None)) -> dict:
    payload = build_end_of_day_payload(load_state(), date_str=date)
    try:
        result = sync_end_of_day_to_notion(payload)
    except NotionSyncError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@app.post("/api/missions/{mission_id}/process")
def process_mission(mission_id: str) -> dict:
    return _process_mission(mission_id)


if CONFIG.serve_frontend and FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")


@app.get("/")
def root() -> FileResponse:
    if not CONFIG.serve_frontend:
        raise HTTPException(status_code=404, detail="frontend disabled")
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/index.html")
def index_file() -> FileResponse:
    if not CONFIG.serve_frontend:
        raise HTTPException(status_code=404, detail="frontend disabled")
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{asset_path:path}")
def frontend_asset(asset_path: str):
    if not CONFIG.serve_frontend:
        raise HTTPException(status_code=404, detail="frontend disabled")
    if asset_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="not found")
    target = FRONTEND_DIR / asset_path
    if target.exists() and target.is_file():
        return FileResponse(target)
    raise HTTPException(status_code=404, detail="not found")
