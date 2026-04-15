from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import shutil
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DATA_DIR = Path(
    os.environ.get("FIELDOPS_DATA_DIR") or (BASE_DIR / "data")
)
CREDENTIALS_PATH = Path(
    os.environ.get("FIELDOPS_CREDENTIALS_PATH") or (BASE_DIR / "credentials.json")
)
SOURCE_TOKEN_PATH = Path(
    os.environ.get("FIELDOPS_CALENDAR_TOKEN_PATH") or (BASE_DIR / "calendar_token.json")
)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarAuthRequiredError(RuntimeError):
    pass


class CalendarDependencyError(RuntimeError):
    pass


def _runtime_token_path() -> Path:
    if SOURCE_TOKEN_PATH.parent.as_posix().startswith("/etc/secrets"):
        RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
        runtime_token = RUNTIME_DATA_DIR / SOURCE_TOKEN_PATH.name
        if SOURCE_TOKEN_PATH.exists():
            source_bytes = SOURCE_TOKEN_PATH.read_bytes()
            runtime_bytes = runtime_token.read_bytes() if runtime_token.exists() else None
            if runtime_bytes != source_bytes:
                shutil.copyfile(SOURCE_TOKEN_PATH, runtime_token)
        return runtime_token
    return SOURCE_TOKEN_PATH


def _require_google_libs():
    try:
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CalendarDependencyError(
            "Missing Google Calendar OAuth dependencies. Install "
            "google-api-python-client google-auth-httplib2 google-auth-oauthlib."
        ) from exc
    return RefreshError, Request, Credentials, InstalledAppFlow, build


def get_calendar_credentials(interactive: bool = False):
    RefreshError, Request, Credentials, InstalledAppFlow, _ = _require_google_libs()
    token_path = _runtime_token_path()

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except RefreshError as exc:
            if not interactive:
                raise CalendarAuthRequiredError(
                    "Google Calendar OAuth token is expired or revoked. "
                    f"Run authorize_calendar.py to replace {token_path}."
                ) from exc
            creds = None

    if not interactive:
        raise CalendarAuthRequiredError(
            f"Google Calendar OAuth authorization is required. Save your desktop OAuth client as "
            f"{CREDENTIALS_PATH} and run authorize_calendar.py to create {token_path}."
        )

    if not CREDENTIALS_PATH.exists():
        raise CalendarAuthRequiredError(
            f"Missing OAuth client file at {CREDENTIALS_PATH}. "
            "Download the Desktop app client JSON from Google Cloud first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_calendar_service(interactive: bool = False):
    _, _, _, _, build = _require_google_libs()
    creds = get_calendar_credentials(interactive=interactive)
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    *,
    title: str,
    start_local: datetime,
    end_local: datetime,
    timezone_str: str,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
) -> dict[str, Any]:
    service = build_calendar_service(interactive=False)
    event = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {
            "dateTime": start_local.isoformat(),
            "timeZone": timezone_str,
        },
        "end": {
            "dateTime": end_local.isoformat(),
            "timeZone": timezone_str,
        },
    }
    created = (
        service.events()
        .insert(calendarId=calendar_id, body=event)
        .execute()
    )
    return {
        "event_id": created.get("id", ""),
        "html_link": created.get("htmlLink", ""),
        "title": created.get("summary", title),
        "start": ((created.get("start") or {}).get("dateTime")) or start_local.isoformat(),
        "end": ((created.get("end") or {}).get("dateTime")) or end_local.isoformat(),
        "calendar_id": calendar_id,
        "timezone": timezone_str,
    }


def list_upcoming_events(
    *,
    calendar_id: str = "primary",
    limit: int = 10,
    days_ahead: int = 7,
) -> list[dict[str, Any]]:
    service = build_calendar_service(interactive=False)
    now_utc = datetime.now(timezone.utc)
    max_utc = now_utc + timedelta(days=max(days_ahead, 1))
    response = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now_utc.isoformat(),
            timeMax=max_utc.isoformat(),
            maxResults=max(limit, 1),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    items = response.get("items", []) or []
    events: list[dict[str, Any]] = []
    for item in items:
        start_info = item.get("start") or {}
        end_info = item.get("end") or {}
        start_dt = (start_info.get("dateTime") or "").strip()
        end_dt = (end_info.get("dateTime") or "").strip()
        all_day_date = (start_info.get("date") or "").strip()
        end_day_date = (end_info.get("date") or "").strip()
        is_all_day = bool(all_day_date and not start_dt)
        date_value = ""
        start_value: str | None = None
        end_value: str | None = None
        if is_all_day:
            date_value = all_day_date
        else:
            try:
                start_obj = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                date_value = start_obj.date().isoformat()
                start_value = start_obj.strftime("%H:%M")
            except ValueError:
                continue
            if end_dt:
                try:
                    end_obj = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
                    end_value = end_obj.strftime("%H:%M")
                except ValueError:
                    end_value = None
        if not date_value:
            continue
        events.append(
            {
                "eventId": str(item.get("id") or ""),
                "source": "calendar_live",
                "date": date_value,
                "start": start_value,
                "end": end_value,
                "title": str(item.get("summary") or "Calendar Event"),
                "loc": str(item.get("location") or ""),
                "dot": "#00c8ff",
                "desc": str(item.get("description") or ""),
                "allDay": is_all_day,
            }
        )
    return events
