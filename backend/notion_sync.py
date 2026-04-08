from __future__ import annotations

from datetime import datetime
from typing import Any

from models import (
    AppState,
    Mission,
    NotionArtifact,
    NotionDaySummary,
    NotionEndOfDayPayload,
    NotionMissionRecord,
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
