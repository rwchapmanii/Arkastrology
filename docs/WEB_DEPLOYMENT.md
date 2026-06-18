# Web Deployment

## Target shape

- Frontend: `www.arkastrology.app`
- Redirect: `arkastrology.app` -> `https://www.arkastrology.app`
- API: `api.arkastrology.app`

This repo now supports a split deployment:

- `apps/mobile` exports a browser SPA
- `apps/api` runs as a standalone FastAPI service

## Recommended providers

- Frontend: Vercel
- API: Render

This is the quickest stable path for the current repo because:

- the Expo app now exports cleanly as a SPA
- the backend is already a single-process FastAPI app
- Render can mount a persistent disk for the API's JSON-backed account/session/history state

## Frontend deployment

### Project root

Set the Vercel project root to:

- `apps/mobile`

### Build settings

The repo now includes [apps/mobile/vercel.json](/Users/ronaldchapman/.openclaw/workspace/astrology-app/apps/mobile/vercel.json), which assumes:

- install: `npm install`
- build: `npm run build:web`
- output: `dist`

### Required frontend environment variable

Set:

```bash
EXPO_PUBLIC_API_BASE_URL=https://api.arkastrology.app
```

Without this, hosted web falls back to same-origin API assumptions, which is not the intended production topology for `www` + `api`.

### Custom domain

Attach:

- `www.arkastrology.app` to the Vercel project
- `arkastrology.app` as a redirect target to `https://www.arkastrology.app`

Use the DNS values Vercel provides in the domain dashboard.

## API deployment

### Blueprint

The repo now includes [render.yaml](/Users/ronaldchapman/.openclaw/workspace/astrology-app/render.yaml) for Render.

It configures:

- root dir: `apps/api`
- start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- health check: `/healthz`
- persistent disk mount
- production CORS defaults for `www.arkastrology.app` and `arkastrology.app`

### Persistent data

The current API still stores:

- users
- sessions
- rate limits
- reading history
- debug email outbox

as JSON files on disk.

That means hosted environments must set a persistent state path. The code now supports:

```bash
ARK_STATE_DIR=/var/data/ark-state
```

Render blueprint config already sets this and mounts a disk at `/var/data`.

### Required API environment variables

At minimum:

```bash
ARK_STATE_DIR=/var/data/ark-state
ALLOWED_ORIGINS=https://www.arkastrology.app,https://arkastrology.app
ALLOWED_ORIGIN_REGEX=https://.*\\.vercel\\.app
EMAIL_DELIVERY_MODE=smtp
EMAIL_FROM_NAME=The Ark
EMAIL_FROM_ADDRESS=support@arkastrology.app
EMAIL_SUPPORT_ADDRESS=support@arkastrology.app
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=support@arkastrology.app
SMTP_PASSWORD=...
SMTP_USE_TLS=true
SMTP_USE_SSL=false
EMAIL_DEBUG_EXPOSE_TOKENS=false
```

### Custom domain

Attach:

- `api.arkastrology.app`

to the Render web service and use the DNS target Render provides.

## DNS plan

Use provider-issued values, but conceptually:

- `www.arkastrology.app` -> frontend host
- `arkastrology.app` -> redirect to `www`
- `api.arkastrology.app` -> API host

## Local development

Frontend:

```bash
cd apps/mobile
npm run web
```

API:

```bash
cd apps/api
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The browser app defaults to local API targets on localhost/127.0.0.1 during development.

## Current limitations

This is a valid deployment baseline, but not the end state.

Important follow-ups:

1. Move auth/session/history persistence off JSON files and onto a real database.
2. Add provider-specific CI/CD or preview-environment rules if you want predictable staging.
3. Add observability and structured logging around auth, reading generation, and email delivery.
4. Decide whether long-term production should stay split-domain or move behind a single origin/proxy.
