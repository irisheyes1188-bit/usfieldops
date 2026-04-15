from __future__ import annotations

from calendar_oauth import (
    SOURCE_TOKEN_PATH,
    get_calendar_credentials,
)


def main() -> None:
    print("Starting Google Calendar OAuth authorization...")
    creds = get_calendar_credentials(interactive=True)
    print("Calendar authorization complete.")
    print(f"Token saved to: {SOURCE_TOKEN_PATH}")
    print(f"Scopes: {', '.join(creds.scopes or [])}")


if __name__ == "__main__":
    main()
