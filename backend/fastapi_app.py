from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import load_config
from models import AppState
from notion_sync import NotionSyncError, build_end_of_day_payload, sync_end_of_day_to_notion
from calendar_oauth import (
    CalendarAuthRequiredError,
    CalendarDependencyError,
    list_upcoming_events,
)
from runner import (
    execute_mission,
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

    result = execute_mission(mission)
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


@app.get("/api/calendar/upcoming")
def get_calendar_upcoming(
    limit: int = Query(default=10, ge=1, le=50),
    days: int = Query(default=7, ge=1, le=30),
) -> dict:
    try:
        events = list_upcoming_events(limit=limit, days_ahead=days)
    except (CalendarAuthRequiredError, CalendarDependencyError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Calendar fetch failed: {exc}") from exc
    return {"ok": True, "events": events}


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
