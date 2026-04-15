from __future__ import annotations

import base64
import os
import shutil
from email.message import EmailMessage
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
    os.environ.get("FIELDOPS_GMAIL_TOKEN_PATH") or (BASE_DIR / "token.json")
)
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


class GmailAuthRequiredError(RuntimeError):
    pass


class GmailDependencyError(RuntimeError):
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
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise GmailDependencyError(
            "Missing Gmail OAuth dependencies. Install "
            "google-api-python-client google-auth-httplib2 google-auth-oauthlib."
        ) from exc
    return Request, Credentials, InstalledAppFlow, build, HttpError


def get_gmail_credentials(interactive: bool = False):
    Request, Credentials, InstalledAppFlow, _, _ = _require_google_libs()
    token_path = _runtime_token_path()

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not interactive:
        raise GmailAuthRequiredError(
            f"Gmail OAuth authorization is required. Save your desktop OAuth client as "
            f"{CREDENTIALS_PATH} and run authorize_gmail.py to create {token_path}."
        )

    if not CREDENTIALS_PATH.exists():
        raise GmailAuthRequiredError(
            f"Missing OAuth client file at {CREDENTIALS_PATH}. "
            "Download the Desktop app client JSON from Google Cloud first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_gmail_service(interactive: bool = False):
    _, _, _, build, _ = _require_google_libs()
    creds = get_gmail_credentials(interactive=interactive)
    return build("gmail", "v1", credentials=creds)


def create_gmail_draft(
    *,
    to: str = "",
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
) -> dict[str, Any]:
    message = EmailMessage()
    if to:
        message["To"] = to
    if cc:
        message["Cc"] = cc
    if bcc:
        message["Bcc"] = bcc
    message["Subject"] = subject
    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    payload = {"message": {"raw": encoded_message}}

    service = build_gmail_service(interactive=False)
    draft = service.users().drafts().create(userId="me", body=payload).execute()
    return {
        "draft_id": draft.get("id", ""),
        "message_id": (draft.get("message") or {}).get("id", ""),
    }
