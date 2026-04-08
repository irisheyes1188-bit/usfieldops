from __future__ import annotations

from datetime import datetime
import json
from urllib import error, request
from typing import Any

from config import load_config
from models import (
    AppState,
    Mission,
    NotionArtifact,
    NotionDaySummary,
    NotionEndOfDayPayload,
    NotionMissionRecord,
    NotionSyncResult,
    TaskItem,
)


def _iso_day(value: datetime | str | None) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return value[:10]
    return datetime.now().date().isoformat()


def _count_as(action_type: str, mission_class: str, lane: str) -> str:
    mapping = {
        "gmail_create_draft": "outreach",
        "calendar_create_event": "calendar",
        "generate_word_report": "deliverable",
        "email_deliverable": "deliverable",
        "log_deliverable": "admin",
        "document_completed_work": "admin",
        "fallback_handoff_email": "admin",
    }
    if action_type in mapping:
        return mapping[action_type]
    if mission_class == "documentation":
        return "admin"
    if lane.lower().startswith("l3"):
        return "study"
    if lane.lower().startswith("l1") or lane.lower().startswith("l4"):
        return "outreach"
    return "deliverable"


def _source_context(mission: Mission) -> str:
    if (mission.sourceContext or "").strip():
        return mission.sourceContext.strip()
    prompt_text = (mission.prompt or "").lower()
    if "gabby" in prompt_text:
        return "mirrored_from_gabby"
    if "maria" in prompt_text:
        return "mirrored_from_maria"
    if "copilot" in prompt_text:
        return "mirrored_from_copilot"
    return "fieldops_native"


def _destination(mission: Mission) -> str:
    details = mission.actionDetails or {}
    if mission.actionType == "gmail_create_draft":
        return str(details.get("to") or "").strip()
    if mission.actionType == "calendar_create_event":
        return str(details.get("calendar_id") or "primary").strip()
    return ""


def _artifact_fields(mission: Mission) -> tuple[str, str, str]:
    details = mission.actionDetails or {}
    if mission.actionType == "gmail_create_draft":
        return (
            str(details.get("draft_id") or ""),
            "",
            "gmail_draft",
        )
    if mission.actionType == "calendar_create_event":
        return (
            str(details.get("event_id") or ""),
            str(details.get("html_link") or details.get("event_url") or ""),
            "calendar_event",
        )
    return ("", "", "")


def _mission_record(mission: Mission, *, status_override: str | None = None) -> NotionMissionRecord:
    mission_class = mission.missionClass or ("execution" if mission.executionType == "action" else "documentation")
    artifact_id, artifact_link, _ = _artifact_fields(mission)
    return NotionMissionRecord(
        mission_id=mission.id,
        mission=mission.title or "Untitled Mission",
        date=_iso_day(mission.completedAt or mission.updatedAt or mission.createdAt),
        agent=(mission.agent or "Chuck").title(),
        mission_class=mission_class,
        action_type=mission.actionType or "",
        status=status_override or mission.status or "queued",
        priority=(mission.priority or "normal").upper(),
        lane=mission.lane or "General Ops",
        source_context=_source_context(mission),
        parent_mission_id=mission.parentMissionId or "",
        count_as=_count_as(mission.actionType or "", mission_class, mission.lane or ""),
        destination=_destination(mission),
        artifact_id=artifact_id,
        artifact_link=artifact_link,
        result_summary=mission.resultSummary or "",
        follow_up=bool(mission.followUp),
    )


def _artifact_record(mission: Mission) -> NotionArtifact | None:
    artifact_id, artifact_link, artifact_label = _artifact_fields(mission)
    if not artifact_id and not artifact_link:
        return None
    return NotionArtifact(
        mission_id=mission.id,
        action_type=mission.actionType or "",
        artifact_id=artifact_id,
        artifact_link=artifact_link,
        artifact_label=artifact_label,
    )


def _completed_task_record(task: TaskItem, day: str) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "title": task.title,
        "date": day,
        "priority": (task.priority or "normal").upper(),
        "lane": task.lane or "General Ops",
        "status": task.status,
        "carry": bool(task.carry),
    }


def build_end_of_day_payload(state: AppState, *, date_str: str | None = None) -> NotionEndOfDayPayload:
    day = date_str or datetime.now().date().isoformat()
    completed = [_mission_record(m, status_override="completed") for m in state.completedMissions]
    active = [_mission_record(m) for m in state.missions]
    artifacts = [record for m in (state.completedMissions + state.missions) if (record := _artifact_record(m))]

    completed_tasks = [
        _completed_task_record(task, day)
        for task in state.myTasks
        if task.status == "done"
    ]
    carry_forward_items = []
    for mission in state.missions:
        if mission.carry or mission.carryForward:
            carry_forward_items.append(
                {
                    "type": "mission",
                    "id": mission.id,
                    "title": mission.title,
                    "lane": mission.lane or "General Ops",
                    "status": mission.status,
                }
            )
    for task in state.myTasks:
        if task.status != "done":
            carry_forward_items.append(
                {
                    "type": "task",
                    "id": task.id,
                    "title": task.title,
                    "lane": task.lane or "General Ops",
                    "status": task.status,
                }
            )

    deliverable_count = sum(1 for m in completed if m.count_as == "deliverable")
    outreach_count = sum(1 for m in completed if m.count_as == "outreach")
    calendar_count = sum(1 for m in completed if m.count_as == "calendar")
    follow_ups = sum(1 for m in completed if m.follow_up)

    summary_parts = [
        f"{len(completed)} completed mission{'s' if len(completed) != 1 else ''}",
        f"{len(completed_tasks)} completed task{'s' if len(completed_tasks) != 1 else ''}",
    ]
    if carry_forward_items:
        summary_parts.append(f"{len(carry_forward_items)} carry-forward item{'s' if len(carry_forward_items) != 1 else ''}")

    payload = NotionEndOfDayPayload(
        day=NotionDaySummary(
            date=day,
            summary=" | ".join(summary_parts),
            mission_count=len(completed),
            deliverable_count=deliverable_count,
            outreach_count=outreach_count,
            calendar_count=calendar_count,
            follow_ups=follow_ups,
            carry_forward_count=len(carry_forward_items),
            status="open",
        ),
        completed_missions=completed,
        active_missions=active,
        completed_tasks=completed_tasks,
        carry_forward_items=carry_forward_items,
        artifacts=artifacts,
    )
    return payload


NOTION_VERSION = "2022-06-28"


class NotionSyncError(RuntimeError):
    pass


def _notion_request(method: str, path: str, *, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"https://api.notion.com/v1{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise NotionSyncError(f"Notion API {method} {path} failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise NotionSyncError(f"Notion API request failed: {exc}") from exc


def _title_prop(value: str) -> dict[str, Any]:
    return {"title": [{"text": {"content": value}}]}


def _rich_text_prop(value: str) -> dict[str, Any]:
    return {"rich_text": [{"text": {"content": value[:1900]}}]} if value else {"rich_text": []}


def _number_prop(value: int) -> dict[str, Any]:
    return {"number": value}


def _checkbox_prop(value: bool) -> dict[str, Any]:
    return {"checkbox": bool(value)}


def _select_prop(value: str) -> dict[str, Any]:
    return {"select": {"name": value}} if value else {"select": None}


def _date_prop(value: str) -> dict[str, Any]:
    return {"date": {"start": value}} if value else {"date": None}


def _url_prop(value: str) -> dict[str, Any]:
    return {"url": value or None}


def _query_database(database_id: str, token: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = _notion_request("POST", f"/databases/{database_id}/query", token=token, payload=payload)
    return response.get("results", [])


def _create_page(database_id: str, token: str, properties: dict[str, Any]) -> dict[str, Any]:
    return _notion_request(
        "POST",
        "/pages",
        token=token,
        payload={"parent": {"database_id": database_id}, "properties": properties},
    )


def _update_page(page_id: str, token: str, properties: dict[str, Any]) -> dict[str, Any]:
    return _notion_request("PATCH", f"/pages/{page_id}", token=token, payload={"properties": properties})


def _daily_log_properties(payload: NotionEndOfDayPayload) -> dict[str, Any]:
    day = payload.day
    return {
        "Date": _date_prop(day.date),
        "Summary": _rich_text_prop(day.summary),
        "Mission Count": _number_prop(day.mission_count),
        "Deliverable Count": _number_prop(day.deliverable_count),
        "Outreach Count": _number_prop(day.outreach_count),
        "Calendar Count": _number_prop(day.calendar_count),
        "Follow-Ups": _number_prop(day.follow_ups),
        "Status": _select_prop(day.status),
        "Notes": _rich_text_prop(
            f"Carry Forward: {day.carry_forward_count} | "
            f"Completed Tasks: {len(payload.completed_tasks)} | "
            f"Artifacts: {len(payload.artifacts)}"
        ),
    }


def _mission_properties(record: NotionMissionRecord) -> dict[str, Any]:
    return {
        "Mission": _title_prop(record.mission),
        "Date": _date_prop(record.date),
        "Agent": _select_prop(record.agent),
        "Mission Class": _select_prop(record.mission_class),
        "Action Type": _select_prop(record.action_type or "document_completed_work"),
        "Status": _select_prop(record.status),
        "Priority": _select_prop(record.priority),
        "Lane": _select_prop(record.lane),
        "Source Context": _select_prop(record.source_context),
        "Parent Mission ID": _rich_text_prop(record.parent_mission_id),
        "Count As": _select_prop(record.count_as),
        "Destination": _rich_text_prop(record.destination),
        "Artifact Link": _url_prop(record.artifact_link),
        "Artifact ID": _rich_text_prop(record.artifact_id),
        "Result Summary": _rich_text_prop(record.result_summary),
        "Follow-Up": _checkbox_prop(record.follow_up),
    }


def _find_daily_log_page(database_id: str, token: str, day: str) -> dict[str, Any] | None:
    results = _query_database(
        database_id,
        token,
        {
            "filter": {
                "property": "Date",
                "date": {"equals": day},
            },
            "page_size": 1,
        },
    )
    return results[0] if results else None


def _find_mission_page(database_id: str, token: str, record: NotionMissionRecord) -> dict[str, Any] | None:
    results = _query_database(
        database_id,
        token,
        {
            "filter": {
                "and": [
                    {"property": "Mission", "title": {"equals": record.mission}},
                    {"property": "Date", "date": {"equals": record.date}},
                    {"property": "Agent", "select": {"equals": record.agent}},
                ]
            },
            "page_size": 1,
        },
    )
    return results[0] if results else None


def sync_end_of_day_to_notion(payload: NotionEndOfDayPayload) -> NotionSyncResult:
    config = load_config()
    if not config.notion_token:
        raise NotionSyncError("FIELDOPS_NOTION_TOKEN is not configured.")
    if not config.notion_daily_log_db_id or not config.notion_mission_ledger_db_id:
        raise NotionSyncError("Notion database IDs are not configured.")

    day_page = _find_daily_log_page(config.notion_daily_log_db_id, config.notion_token, payload.day.date)
    daily_log_page_id = ""
    if day_page:
        daily_log_page_id = day_page.get("id", "")
        _update_page(daily_log_page_id, config.notion_token, _daily_log_properties(payload))
    else:
        created = _create_page(
            config.notion_daily_log_db_id,
            config.notion_token,
            _daily_log_properties(payload),
        )
        daily_log_page_id = created.get("id", "")

    created_count = 0
    updated_count = 0
    for record in payload.completed_missions:
        existing = _find_mission_page(config.notion_mission_ledger_db_id, config.notion_token, record)
        props = _mission_properties(record)
        if existing:
            _update_page(existing.get("id", ""), config.notion_token, props)
            updated_count += 1
        else:
            _create_page(config.notion_mission_ledger_db_id, config.notion_token, props)
            created_count += 1

    return NotionSyncResult(
        ok=True,
        date=payload.day.date,
        daily_log_page_id=daily_log_page_id,
        mission_pages_created=created_count,
        mission_pages_updated=updated_count,
        completed_missions_considered=len(payload.completed_missions),
        message="Notion sync completed successfully.",
    )
