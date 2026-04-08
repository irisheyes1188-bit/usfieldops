# FieldOps Hosted Backend Deployment

This is the Phase 4 deployment runbook for hosting the FieldOps backend behind:

- `https://api.usfieldops.com`

The current production shape is:

- `https://usfieldops.com` -> static front-end
- `https://api.usfieldops.com` -> FastAPI backend

## What the hosted backend must provide

- `GET /api/health`
- `GET /api/state`
- `POST /api/state`
- `POST /api/missions/{id}/process`
- `GET /api/notion/end-of-day`
- `POST /api/notion/end-of-day/sync`

## Recommended deployment model

Recommended host: **Render**

Why this is the best current fit:

- supports Docker web services
- supports persistent disks for SQLite
- supports custom domains for `api.usfieldops.com`
- supports secret files for mounted OAuth credentials/tokens

The project now includes a ready blueprint file at:

- `render.yaml`

Use one small Python container with:

- a persistent writable volume mounted at `/data`
- secrets mounted outside the image
- custom domain pointing to the container/app host

This keeps the stack simple while preserving:

- SQLite runtime state
- Gmail draft creation
- Google Calendar event creation
- Notion sync/export

## Container build

Build from the project root:

```powershell
docker build -t fieldops-backend .
```

Run locally in hosted-style mode:

```powershell
docker run --rm -p 8765:8765 `
  -e FIELDOPS_ENV=production `
  -e FIELDOPS_HOST=0.0.0.0 `
  -e FIELDOPS_PORT=8765 `
  -e FIELDOPS_PUBLIC_APP_URL=https://usfieldops.com `
  -e FIELDOPS_API_BASE_URL=https://api.usfieldops.com/api `
  -e FIELDOPS_ALLOWED_ORIGINS=https://usfieldops.com,https://www.usfieldops.com `
  -e FIELDOPS_SERVE_FRONTEND=false `
  -e FIELDOPS_DATA_DIR=/data `
  -v C:\fieldops-data:/data `
  -v C:\fieldops-secrets:/secrets `
  fieldops-backend
```

## Render deployment path

1. Push the current project to the repo you want Render to deploy from.
2. In Render, create a new Blueprint deployment from that repo.
3. Use the included `render.yaml`.
4. After the service is created, add secret files in Render for:
   - `credentials.json`
   - `token.json`
   - `calendar_token.json`
5. Confirm the mounted secret file paths match:
   - `/etc/secrets/credentials.json`
   - `/etc/secrets/token.json`
   - `/etc/secrets/calendar_token.json`
6. Add the custom domain:
   - `api.usfieldops.com`
7. Point DNS for `api.usfieldops.com` at the Render service.
8. Verify:
   - `https://api.usfieldops.com/api/health`
   - `https://api.usfieldops.com/api/state`
   - `POST https://api.usfieldops.com/api/notion/end-of-day/sync`

## Required hosted environment variables

Baseline:

- `FIELDOPS_ENV=production`
- `FIELDOPS_HOST=0.0.0.0`
- `FIELDOPS_PORT=8765`
- `FIELDOPS_PUBLIC_APP_URL=https://usfieldops.com`
- `FIELDOPS_API_BASE_URL=https://api.usfieldops.com/api`
- `FIELDOPS_ALLOWED_ORIGINS=https://usfieldops.com,https://www.usfieldops.com`
- `FIELDOPS_SERVE_FRONTEND=false`
- `FIELDOPS_RELOAD=false`
- `FIELDOPS_DATA_DIR=/data`
- `FIELDOPS_NOTION_TOKEN=<your notion integration token>`
- `FIELDOPS_NOTION_DAILY_LOG_DB_ID=dc9bbfed-8219-4cb6-add4-89d1d6b89284`
- `FIELDOPS_NOTION_MISSION_LEDGER_DB_ID=777768e7-1d47-4dd7-8411-f575dbd551b5`

## Required hosted secrets/files

These must not be baked into the image or committed to git.

Place them on the host or mount them into the container:

- `credentials.json`
- `token.json`
- `calendar_token.json`

Recommended mount target:

- `/secrets/credentials.json`
- `/secrets/token.json`
- `/secrets/calendar_token.json`

If you use mounted secrets, set:

- `FIELDOPS_CREDENTIALS_PATH`
- `FIELDOPS_GMAIL_TOKEN_PATH`
- `FIELDOPS_CALENDAR_TOKEN_PATH`

## Persistent storage

FieldOps runtime state should live on a persistent volume, not inside the container.

Recommended:

- `/data/fieldops.db`

This is the live operational store for:

- missions
- tasks
- agenda state
- focus state
- template/meta state

Legacy JSON import still comes from the project copy of:

- `backend/data/state.json`

## DNS / domain wiring

Recommended:

- `usfieldops.com` stays on Netlify/static hosting
- `api.usfieldops.com` points to the backend host

For Render:

- keep the existing Netlify site for `usfieldops.com`
- add `api.usfieldops.com` as a Render custom domain
- update DNS to the target Render provides

## Front-end cutover

Once the backend is live:

1. Set the front-end API base to:
   - `https://api.usfieldops.com/api`
2. Verify:
   - `GET https://api.usfieldops.com/api/health`
   - website load
   - state load/save
   - Gmail draft creation
   - Calendar event creation
   - Notion end-of-day export

## Recommended go-live smoke test

1. Open:
   - `https://api.usfieldops.com/api/health`
2. Open:
   - `https://usfieldops.com/?api_base=https://api.usfieldops.com/api`
3. Load a Gmail mission and confirm a real draft is created.
4. Load a Calendar mission and confirm a real event is created.
5. Open:
   - `https://api.usfieldops.com/api/notion/end-of-day`
6. Confirm the payload looks correct.

## Phase 4 exit criteria

Phase 4 is ready when:

- the container builds cleanly
- the API responds on the hosted domain
- the front-end can point at the hosted API
- Gmail and Calendar actions still succeed
- end-of-day export still works
