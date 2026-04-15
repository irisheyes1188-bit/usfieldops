from __future__ import annotations

import json
import mimetypes
import re
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from calendar_oauth import (
    CalendarAuthRequiredError,
    CalendarDependencyError,
    list_upcoming_events,
)
from config import load_config
from models import AppState
from notion_sync import NotionSyncError, build_end_of_day_payload, sync_end_of_day_to_notion
from runner import (
    execute_mission,
)
from storage import ensure_state_file, load_state, save_state


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CONFIG = load_config()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def log_request_line(self, method: str, path: str) -> None:
        print(f"{method} {path}", flush=True)

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_json({"error": "not found"}, 404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        self.log_request_line("GET", path)
        if path == "/api/health":
            self.send_json({"ok": True, "service": "fieldops-backend"})
            return
        if path == "/api/state":
            self.send_json(load_state().model_dump(mode="json"))
            return
        if path == "/api/calendar/upcoming":
            try:
                limit = int(query.get("limit", ["10"])[0])
                days = int(query.get("days", ["7"])[0])
            except ValueError:
                self.send_json({"error": "invalid query parameters"}, 400)
                return
            if limit < 1 or limit > 50 or days < 1 or days > 30:
                self.send_json({"error": "query parameters out of range"}, 400)
                return
            try:
                events = list_upcoming_events(limit=limit, days_ahead=days)
            except (CalendarAuthRequiredError, CalendarDependencyError) as exc:
                self.send_json({"error": str(exc)}, 503)
                return
            except Exception as exc:
                self.send_json({"error": f"Calendar fetch failed: {exc}"}, 500)
                return
            self.send_json({"ok": True, "events": events})
            return
        if path == "/api/notion/end-of-day":
            state = load_state()
            day = query.get("date", [None])[0]
            payload = build_end_of_day_payload(state, date_str=day)
            self.send_json(payload.model_dump(mode="json"))
            return
        if path == "/" or path == "/index.html":
            self.send_file(FRONTEND_DIR / "index.html")
            return
        self.send_file(FRONTEND_DIR / path.lstrip("/"))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        self.log_request_line("POST", path)
        if path == "/api/state":
            state = AppState.model_validate(self.read_json())
            saved = save_state(state)
            self.send_json({"ok": True, "state": saved.model_dump(mode="json")})
            return
        if path == "/api/notion/end-of-day/sync":
            day = query.get("date", [None])[0]
            payload = build_end_of_day_payload(load_state(), date_str=day)
            try:
                result = sync_end_of_day_to_notion(payload)
            except NotionSyncError as exc:
                self.send_json({"error": str(exc)}, 500)
                return
            self.send_json(result.model_dump(mode="json"))
            return
        if re.match(r"^/api/missions/[^/]+/process$", path):
            mission_id = path.split("/")[-2]
            state = load_state()
            mission = next((m for m in state.missions if m.id == mission_id), None)
            if mission is None:
                self.send_json({"error": "mission not found"}, 404)
                return

            result = execute_mission(mission)
            saved = save_state(state)
            saved_mission = next((m for m in saved.missions if m.id == mission_id), None)
            self.send_json(
                {
                    "ok": True,
                    "mission": saved_mission.model_dump(mode="json") if saved_mission else None,
                    "result": result,
                }
            )
            return
        self.send_json({"error": "not found"}, 404)


def run() -> None:
    ensure_state_file()
    host = CONFIG.host
    port = CONFIG.port
    localhost_url = f"http://127.0.0.1:{port}/api/health"
    lan_ip = ""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        lan_ip = probe.getsockname()[0]
        probe.close()
    except OSError:
        lan_ip = ""
    lan_health_url = f"http://{lan_ip}:{port}/api/health" if lan_ip else ""
    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError as exc:
        print("FieldOps backend failed to start", flush=True)
        print(f"Host: {host}", flush=True)
        print(f"Port: {port}", flush=True)
        print(f"Reason: {exc}", flush=True)
        raise SystemExit(1) from exc

    print("FieldOps backend started", flush=True)
    print(f"Host: {host}", flush=True)
    print(f"Port: {port}", flush=True)
    print(f"Local Health: {localhost_url}", flush=True)
    if lan_health_url:
        print(f"LAN Health: {lan_health_url}", flush=True)
        print(f"Mobile URL: http://{lan_ip}:{port}", flush=True)
    print("Press Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFieldOps backend stopped", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
