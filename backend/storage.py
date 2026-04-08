from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from models import AppState


BASE_DIR = Path(__file__).resolve().parent
LEGACY_DATA_DIR = BASE_DIR / "data"
STATE_PATH = LEGACY_DATA_DIR / "state.json"
RUNTIME_DATA_DIR = Path(
    os.environ.get("FIELDOPS_DATA_DIR")
    or (Path(os.environ.get("LOCALAPPDATA", str(LEGACY_DATA_DIR))) / "FieldOps" / "data")
)
DB_PATH = RUNTIME_DATA_DIR / "fieldops.db"
_LOCK = threading.Lock()


DEFAULT_STATE = AppState(
    templates={
        "gabby": [
            {
                "name": "Call Sheet Intel",
                "desc": "Research companies, identify decision makers connected to energy or housing.",
                "objective": "Research the following companies and identify decision makers connected to energy efficiency, housing initiatives, or commercial construction.",
                "output": "Return a structured table: Company | Key Contact | Title | Email | Notes | Connection to housing or energy programs",
            },
            {
                "name": "Morning Brief",
                "desc": "Compile priority items, calendar, and outstanding tasks.",
                "objective": "Compile a morning brief: upcoming calendar events, priority tasks, outstanding outreach follow-ups, and one recommended focus item for the day.",
                "output": "Return: Schedule | Priority Tasks | Open Outreach | Recommended Focus",
            },
            {
                "name": "Outreach Strategy",
                "desc": "Build an outreach plan for a specific prospect.",
                "objective": "Build an outreach strategy for the following prospect. Identify the best angle, talking points, and recommended next steps.",
                "output": "Return: Prospect Summary | Best Angle | Key Talking Points | Recommended Outreach Sequence | Expected Objections",
            },
        ],
        "chuck": [
            {
                "name": "L1 - NEEA Circuit Rider",
                "desc": "Energy code outreach, circuit rider activities, technical assistance.",
                "objective": "Review the following circuit rider activity and prepare a structured summary suitable for NEEA reporting. Include contacts made, technical assistance provided, and follow-up items.",
                "output": "Return: Activity Summary | Contacts | TA Provided | Follow-Up Items | Billing Notes | Lane: L1",
            },
            {
                "name": "L2 - NWE Rebate Facilitation",
                "desc": "Commercial rebate facilitation, application review, contact outreach.",
                "objective": "Review the following NWE commercial rebate activity and prepare a structured summary. Include project details, rebate status, and next steps.",
                "output": "Return: Project Summary | Rebate Status | Key Contacts | Next Steps | Lane: L2",
            },
            {
                "name": "L3 - IECC Study / Exam Prep",
                "desc": "IECC certification study, exam prep, code section review.",
                "objective": "Generate a structured IECC study block covering the following topics. Use 2021 IECC Residential as the primary reference. Include code section citations.",
                "output": "Return: Topic Summary | Key Code Sections | Practice Questions | Common Exam Traps | Lane: L3",
            },
            {
                "name": "L4 - REAP Tribal Outreach",
                "desc": "REAP program outreach, tribal energy contacts, follow-up tracking.",
                "objective": "Review the following REAP outreach activity and prepare a structured summary. Include contacts, program eligibility notes, and follow-up schedule.",
                "output": "Return: Outreach Summary | Contacts | Eligibility Notes | Follow-Up Schedule | Lane: L4",
            },
            {
                "name": "Weekly Report",
                "desc": "Generate a structured weekly work summary.",
                "objective": "Generate a weekly work summary from the following activity log. Group by project lane, highlight completed deliverables, and include billing justification.",
                "output": "Return: Executive Summary | Work by Project (L1-L4) | Deliverables | Meetings | Carry-Forward | Billing Justification",
            },
            {
                "name": "Build / Modify App Feature",
                "desc": "Design or modify a feature in the FieldOps app.",
                "objective": "Design and implement the following app feature or modification. Preserve existing functionality. Document what was changed and why.",
                "output": "Return: Feature spec | Implementation approach | Code / markup | What was preserved | Open questions",
            },
            {
                "name": "Structure Data",
                "desc": "Take raw data and return a clean structured format.",
                "objective": "Take the following raw data and return it in a clean, structured format suitable for logging or reporting.",
                "output": "Return: Structured table or JSON | Field descriptions | Data quality notes",
            },
        ],
        "gary": [
            {
                "name": "Presentation Builder",
                "desc": "Build a slide deck from provided content.",
                "objective": "Build a presentation from the following content. Clear narrative arc, professional structure, minimal text per slide.",
                "output": "Return: Slide outline | Slide titles + key points | Speaker notes | Recommended visuals per slide",
            },
            {
                "name": "Transcript Summary",
                "desc": "Summarize a meeting transcript into key points.",
                "objective": "Summarize the following meeting transcript. Pull key decisions, action items, and next steps.",
                "output": "Return: Meeting Summary | Key Decisions | Action Items (owner + deadline) | Open Questions | Next Steps",
            },
        ],
        "claude": [
            {
                "name": "Weekly Summary",
                "desc": "Generate a clean weekly summary for stakeholder reporting.",
                "objective": "Generate a clean, professional weekly summary suitable for stakeholder reporting. Concise and factual.",
                "output": "Return: Week overview | Completed items | In-progress | Blockers | Next week priorities",
            },
            {
                "name": "Document Cleanup",
                "desc": "Clean up and improve a document for professional delivery.",
                "objective": "Clean up the following document for professional delivery. Improve clarity, fix grammar, tighten structure. Do not change meaning.",
                "output": "Return: Cleaned document | List of changes | Sections flagged for review",
            },
            {
                "name": "Billing Justification",
                "desc": "Build a billing justification from work log entries.",
                "objective": "Build a billing justification from the following work log entries. Group by project, explain why each activity was legitimate.",
                "output": "Return: Per-project justification | Hours breakdown | Supporting context | Flagged entries",
            },
        ],
    },
    meta={"version": "phase2-sqlite"},
)


def _connect() -> sqlite3.Connection:
    RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def _normalize_payload(payload: dict) -> tuple[AppState, bool]:
    needs_save = False
    if not payload.get("templates"):
        payload["templates"] = DEFAULT_STATE.model_dump(mode="json")["templates"]
        needs_save = True
    if not payload.get("meta"):
        payload["meta"] = DEFAULT_STATE.meta
        needs_save = True
    state = AppState.model_validate(payload)
    return state, needs_save


def _write_state_to_db(state: AppState) -> None:
    payload = json.dumps(state.model_dump(mode="json"), indent=2)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO app_state (id, payload, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = CURRENT_TIMESTAMP
            """,
            (payload,),
        )
        conn.commit()
    finally:
        conn.close()


def ensure_state_file() -> Path:
    LEGACY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute("SELECT payload FROM app_state WHERE id = 1").fetchone()
        finally:
            conn.close()
        if row:
            return DB_PATH
        if STATE_PATH.exists():
            legacy_payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            state, needs_save = _normalize_payload(legacy_payload)
            _write_state_to_db(state)
            if needs_save:
                STATE_PATH.write_text(
                    json.dumps(state.model_dump(mode="json"), indent=2),
                    encoding="utf-8",
                )
            return DB_PATH
        _write_state_to_db(DEFAULT_STATE)
    return DB_PATH


def load_state() -> AppState:
    ensure_state_file()
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute("SELECT payload FROM app_state WHERE id = 1").fetchone()
        finally:
            conn.close()
    payload = json.loads(row[0]) if row and row[0] else DEFAULT_STATE.model_dump(mode="json")
    state, needs_save = _normalize_payload(payload)
    if needs_save:
        save_state(state)
    return state


def save_state(state: AppState) -> AppState:
    LEGACY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        _write_state_to_db(state)
    return state
