from __future__ import annotations

from gmail_oauth import (
    CREDENTIALS_PATH,
    SCOPES,
    SOURCE_TOKEN_PATH,
    GmailAuthRequiredError,
    build_gmail_service,
)


def main() -> None:
    print("FieldOps Gmail OAuth authorization", flush=True)
    print(f"Credentials file: {CREDENTIALS_PATH}", flush=True)
    print(f"Token file: {SOURCE_TOKEN_PATH}", flush=True)
    print(f"Scopes: {', '.join(SCOPES)}", flush=True)
    print("A browser window will open for Google sign-in.", flush=True)
    print("Sign in with irisheyes1188@gmail.com and approve Gmail draft access.", flush=True)
    try:
        service = build_gmail_service(interactive=True)
        profile = service.users().getProfile(userId="me").execute()
        print("Gmail authorization complete", flush=True)
        print(f"Authorized account: {profile.get('emailAddress', 'unknown')}", flush=True)
        print(f"Token saved to: {SOURCE_TOKEN_PATH}", flush=True)
    except GmailAuthRequiredError as exc:
        print(str(exc), flush=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
