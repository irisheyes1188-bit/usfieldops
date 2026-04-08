from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_ALLOWED_ORIGINS = (
    "http://127.0.0.1:8765",
    "http://localhost:8765",
    "https://usfieldops.com",
    "https://www.usfieldops.com",
)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_allowed_origins(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class FieldOpsConfig:
    host: str
    port: int
    environment: str
    public_app_url: str
    api_base_url: str
    allowed_origins: list[str]
    serve_frontend: bool
    reload: bool
    notion_token: str
    notion_daily_log_db_id: str
    notion_mission_ledger_db_id: str


def load_config() -> FieldOpsConfig:
    host = os.getenv("FIELDOPS_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = int((os.getenv("FIELDOPS_PORT") or os.getenv("PORT") or "8765").strip())
    public_app_url = os.getenv("FIELDOPS_PUBLIC_APP_URL", "https://usfieldops.com").strip()
    api_base_url = os.getenv("FIELDOPS_API_BASE_URL", "").strip()
    if not api_base_url:
        api_base_url = f"http://127.0.0.1:{port}/api"
    return FieldOpsConfig(
        host=host,
        port=port,
        environment=os.getenv("FIELDOPS_ENV", "development").strip() or "development",
        public_app_url=public_app_url,
        api_base_url=api_base_url,
        allowed_origins=_parse_allowed_origins(os.getenv("FIELDOPS_ALLOWED_ORIGINS")),
        serve_frontend=_parse_bool(os.getenv("FIELDOPS_SERVE_FRONTEND"), True),
        reload=_parse_bool(os.getenv("FIELDOPS_RELOAD"), False),
        notion_token=os.getenv("FIELDOPS_NOTION_TOKEN", "").strip(),
        notion_daily_log_db_id=os.getenv(
            "FIELDOPS_NOTION_DAILY_LOG_DB_ID",
            "45e1e6f0-312d-454c-bd97-1edef917c2d5",
        ).strip(),
        notion_mission_ledger_db_id=os.getenv(
            "FIELDOPS_NOTION_MISSION_LEDGER_DB_ID",
            "6c5f623f-d7b0-46da-8e83-85fa7d474693",
        ).strip(),
    )
