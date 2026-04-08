# FieldOps

Phase 1 scaffold for turning FieldOps Command Deck v4.4 into a local app with a lightweight Python backend.

## Structure

```text
fieldops/
  frontend/
    index.html
    app.js
    styles.css
  backend/
    main.py
    storage.py
    models.py
    runner.py
    data/
      state.json
  README.md
```

## Current scaffold status

- `frontend/index.html` contains the preserved v4.4 prototype payload.
- `frontend/app.js` and `frontend/styles.css` are reserved for the upcoming split.
- `backend/main.py` exposes the current local HTTP server used for laptop-first operation.
- `backend/fastapi_app.py` exposes the hosted-ready FastAPI backend.
- `backend/start_fastapi.py` starts the FastAPI backend using shared environment config.
- `backend/storage.py` imports legacy JSON state from `backend/data/state.json` and stores live runtime state in SQLite.
- `backend/models.py` defines the Phase 1 state models.
- `backend/runner.py` contains the safe mock mission result builder for the dispatch loop.

## Hosted backend Phase 1

FieldOps now has the first hosted-backend prep layer in place:

- a FastAPI app entrypoint at `backend/fastapi_app.py`
- a Python dependency list at `backend/requirements.txt`
- a configurable frontend API target

The front-end now resolves its backend in this order:

1. `?api_base=https://.../api` query parameter
2. `window.FIELDOPS_API_BASE`
3. `localStorage.fieldops_api_base`
4. fallback to local `/api`

### Local mode

Keep using the current local server:

```powershell
python C:\Users\glegr\OneDrive\Documentos\fieldops\backend\main.py
```

### Hosted mode

Install dependencies:

```powershell
pip install -r C:\Users\glegr\OneDrive\Documentos\fieldops\backend\requirements.txt
```

Run the hosted-ready API locally for testing:

```powershell
python C:\Users\glegr\OneDrive\Documentos\fieldops\backend\start_fastapi.py
```

from:

```text
C:\Users\glegr\OneDrive\Documentos\fieldops\backend
```

### Suggested deployment shape

- `usfieldops.com` -> static front-end
- `api.usfieldops.com` -> FastAPI backend

### Hosted config

Use `backend/.env.example` as the baseline for hosted configuration.

Important runtime variables:

- `FIELDOPS_ENV`
- `FIELDOPS_HOST`
- `FIELDOPS_PORT`
- `FIELDOPS_PUBLIC_APP_URL`
- `FIELDOPS_API_BASE_URL`
- `FIELDOPS_ALLOWED_ORIGINS`
- `FIELDOPS_SERVE_FRONTEND`
- `FIELDOPS_RELOAD`
- optional `FIELDOPS_DATA_DIR`
- optional `FIELDOPS_CREDENTIALS_PATH`
- optional `FIELDOPS_GMAIL_TOKEN_PATH`
- optional `FIELDOPS_CALENDAR_TOKEN_PATH`

### Hosted deployment checklist

1. Deploy the backend from `backend/start_fastapi.py` or equivalent `uvicorn` startup.
2. Move backend secrets into host environment or secure files:
   - Gmail OAuth credentials/token
   - Google Calendar OAuth credentials/token
   - Notion token/config
3. Point the front-end to the hosted API:
   - query param for testing
   - stored API base for stable use
4. Verify:
   - `GET /api/health`
   - `GET /api/state`
   - `POST /api/state`
   - `POST /api/missions/{id}/process`
   - `GET /api/notion/end-of-day`

### Current limitation

The live website can now run the updated front-end, but without a hosted backend it cannot persist state or execute missions from the public site. The laptop backend remains the active system brain until the hosted API is deployed.

## Hosted backend Phase 2

FieldOps now uses SQLite for live runtime state instead of writing the active database into the OneDrive-backed project folder.

- Legacy/import path: `backend/data/state.json`
- Runtime SQLite path by default:

```text
%LOCALAPPDATA%\FieldOps\data\fieldops.db
```

- Optional override:

```text
FIELDOPS_DATA_DIR=<custom writable folder>
```

This avoids OneDrive file-lock and `sqlite3.OperationalError: disk I/O error` issues while keeping existing JSON state available for import/migration.

## Hosted backend Phase 3

FieldOps now shares one explicit backend config layer for local and hosted runs.

Files added for deployment hardening:

- `backend/config.py`
- `backend/start_fastapi.py`
- `backend/.env.example`

What this gives you:

- one set of env vars for local and hosted backends
- explicit CORS origin control
- explicit host/port config
- optional frontend serving toggle for API-only deployment
- a production-friendly FastAPI startup path

Recommended hosted run command:

```powershell
python C:\Users\glegr\OneDrive\Documentos\fieldops\backend\start_fastapi.py
```

or equivalent host command:

```powershell
uvicorn fastapi_app:app --host 0.0.0.0 --port 8765
```

## Hosted backend Phase 4/5

FieldOps now includes deployment packaging for a Render-based hosted backend.

Files added:

- `Dockerfile`
- `.dockerignore`
- `render.yaml`
- `backend/DEPLOYMENT.md`

Current recommended host:

- `Render` for `api.usfieldops.com`

Reason:

- Docker support
- persistent disk support for SQLite
- custom domain support
- secret file support for OAuth credentials/tokens

## Next priority

Wire the frontend state transitions to the backend so missions, tasks, agenda, focus, templates, debrief, and archive persist across refresh and restart.

## Gmail OAuth setup

FieldOps now supports a real Gmail Drafts action path for Gmail draft missions. This uses OAuth 2.0 user authorization, not an API key.

### Google Cloud setup

1. Use a Google Cloud project with the Gmail API enabled.
2. Configure the OAuth consent screen.
3. Create an OAuth Client ID for a Desktop app.
4. Save the downloaded OAuth client JSON file as:

```text
fieldops/backend/credentials.json
```

### Python dependencies

Install these packages in the Python environment you use to run the backend:

```powershell
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### One-time Gmail authorization

Run:

```powershell
python C:\Users\glegr\OneDrive\Documentos\fieldops\backend\authorize_gmail.py
```

That script will:

- open a browser window
- let you sign in as `irisheyes1188@gmail.com`
- request the Gmail compose scope
- save the authorized token to:

```text
fieldops/backend/token.json
```

Required scope:

```text
https://www.googleapis.com/auth/gmail.compose
```

### Notes

- If scopes change later, delete `backend/token.json` and authorize again.
- Gmail draft missions must report success only after a real Gmail draft is created.
- If OAuth is not configured yet, Gmail draft missions will return an auth/action-required result instead of a mock success.

## Google Calendar OAuth setup

FieldOps now supports a real Google Calendar event creation path for calendar action missions.

### Required scope

```text
https://www.googleapis.com/auth/calendar.events
```

### One-time Calendar authorization

Use the same Desktop OAuth client JSON at:

```text
fieldops/backend/credentials.json
```

Then run:

```powershell
python C:\Users\glegr\OneDrive\Documentos\fieldops\backend\authorize_calendar.py
```

That script will:

- open a browser window
- let you sign in to the Google account that owns the calendar
- request Calendar event write access
- save the authorized token to:

```text
fieldops/backend/calendar_token.json
```

### Notes

- Calendar event missions must report success only after a real event is created.
- If Calendar OAuth is not configured yet, calendar missions now return an auth/action-required result instead of a mock success.
- If you change Calendar scopes later, delete `backend/calendar_token.json` and authorize again.
