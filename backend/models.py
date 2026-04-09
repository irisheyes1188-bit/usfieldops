from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Mission(BaseModel):
    id: str
    title: str
    agent: str
    missionClass: str = ""
    sourceContext: str = ""
    parentMissionId: str = ""
    template: str = ""
    objective: str = ""
    inputs: str = ""
    expectedOutput: str = ""
    priority: str = "normal"
    lane: str = ""
    due: str = ""
    status: str = "queued"
    carry: bool = False
    prompt: str = ""
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    resultSummary: str = ""
    resultBody: str = ""
    followUp: bool = False
    carryForward: bool = False
    completedAt: datetime | None = None
    mockResult: dict[str, Any] | None = None
    executionType: str = "result"
    actionType: str = ""
    actionStatus: str = ""
    actionDetails: dict[str, Any] | None = None


class TaskItem(BaseModel):
    id: str
    title: str
    priority: str = "normal"
    lane: str = ""
    due: str = ""
    status: str = "todo"
    carry: bool = False
    createdAt: datetime | None = None
    carriedFrom: str = ""


class ActivityItem(BaseModel):
    id: str
    title: str
    owner: str = ""
    lane: str = ""
    type: str = "note"
    status: str = "open"
    timestamp: str = ""
    location: str = ""
    contact: str = ""
    organization: str = ""
    notes: str = ""
    followUp: bool = False
    createdAt: datetime | None = None


class AgendaEvent(BaseModel):
    eventId: str = ""
    source: str = ""
    date: str
    start: str | None = None
    end: str | None = None
    title: str
    loc: str = ""
    dot: str = "#00c8ff"
    desc: str = ""
    allDay: bool = False


class TemplateItem(BaseModel):
    name: str
    desc: str = ""
    objective: str = ""
    output: str = ""
    priority: str = "normal"
    lane: str = ""
    custom: bool = False


class FocusState(BaseModel):
    criticalId: str | None = None
    focusTextOnly: str | None = None


class ArchiveItem(BaseModel):
    id: str
    type: str
    title: str
    lane: str = ""
    priority: str = "normal"
    agent: str = ""
    archivedDate: datetime | None = None
    archivedDateLabel: str = ""
    resultSummary: str = ""
    followUp: bool = False
    completedAt: datetime | None = None
    carry: bool = False
    due: str = ""


class AppState(BaseModel):
    missions: list[Mission] = Field(default_factory=list)
    completedMissions: list[Mission] = Field(default_factory=list)
    myTasks: list[TaskItem] = Field(default_factory=list)
    activityItems: list[ActivityItem] = Field(default_factory=list)
    archivedItems: list[ArchiveItem] = Field(default_factory=list)
    CALENDAR_EVENTS: list[AgendaEvent] = Field(default_factory=list)
    focus: FocusState = Field(default_factory=FocusState)
    templates: dict[str, list[TemplateItem]] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class NotionArtifact(BaseModel):
    mission_id: str
    action_type: str = ""
    artifact_id: str = ""
    artifact_link: str = ""
    artifact_label: str = ""


class NotionMissionRecord(BaseModel):
    mission_id: str
    mission: str
    date: str
    agent: str
    mission_class: str
    action_type: str
    status: str
    priority: str
    lane: str
    source_context: str
    parent_mission_id: str = ""
    count_as: str
    destination: str = ""
    artifact_id: str = ""
    artifact_link: str = ""
    result_summary: str = ""
    follow_up: bool = False


class NotionDaySummary(BaseModel):
    date: str
    summary: str
    mission_count: int
    deliverable_count: int
    outreach_count: int
    calendar_count: int
    follow_ups: int
    carry_forward_count: int
    status: str = "open"


class NotionEndOfDayPayload(BaseModel):
    day: NotionDaySummary
    completed_missions: list[NotionMissionRecord] = Field(default_factory=list)
    active_missions: list[NotionMissionRecord] = Field(default_factory=list)
    completed_tasks: list[dict[str, Any]] = Field(default_factory=list)
    carry_forward_items: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[NotionArtifact] = Field(default_factory=list)


class NotionSyncResult(BaseModel):
    ok: bool
    date: str
    daily_log_page_id: str = ""
    mission_pages_created: int = 0
    mission_pages_updated: int = 0
    completed_missions_considered: int = 0
    message: str = ""
