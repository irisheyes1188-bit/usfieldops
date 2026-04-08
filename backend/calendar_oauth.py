from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_PATH = Path(
    os.environ.get("FIELDOPS_CREDENTIALS_PATH") or (BASE_DIR / "credentials.json")
)
TOKEN_PATH = Path(
    os.environ.get("FIELDOPS_CALENDAR_TOKEN_PATH") or (BASE_DIR / "calendar_token.json")
)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarAuthRequiredError(RuntimeError):
    pass


class CalendarDependencyError(RuntimeError):
    pass


def _require_google_libs():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise CalendarDependencyError(
            "Missing Google Calendar OAuth dependencies. Install "
            "google-api-python-client google-auth-httplib2 google-auth-oauthlib."
        ) from exc
    return Request, Credentials, InstalledAppFlow, build


def get_calendar_credentials(interactive: bool = False):
    Request, Credentials, InstalledAppFlow, _ = _require_google_libs()

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not interactive:
        raise CalendarAuthRequiredError(
            f"Google Calendar OAuth authorization is required. Save your desktop OAuth client as "
            f"{CREDENTIALS_PATH} and run authorize_calendar.py to create {TOKEN_PATH}."
        )

    if not CREDENTIALS_PATH.exists():
        raise CalendarAuthRequiredError(
            f"Missing OAuth client file at {CREDENTIALS_PATH}. "
            "Download the Desktop app client JSON from Google Cloud first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_calendar_service(interactive: bool = False):
    _, _, _, build = _require_google_libs()
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
