# PulseTrack AI

Uptime monitoring + public status page SaaS with an **AI incident analyst** (Gemini).
Add a URL → workers ping it every minute → outages open incidents automatically →
alerts fire via **Telegram Bot** → AI explains the root cause → customers see a
public status page. Full plan: `PulseTrack-AI-Roadmap.pdf`. Progress: `PROGRESS_LOG.md`.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL 16 · Redis 7 · ARQ workers ·
React + TS + Vite (Phase 2+) · Gemini 2.0 Flash · uv · Docker · GitHub Actions · Northflank Sandbox (api+worker) + Vercel (frontend) + Neon (DB) + Upstash (Redis) — $0/month

## Run locally (Phase 8 state — + CSV export, 88% coverage)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) running, [uv](https://docs.astral.sh/uv/) installed.

```bash
# 1) create Telegram bot via @BotFather → paste token + username into backend/.env:
#    TELEGRAM_BOT_TOKEN=...  TELEGRAM_BOT_USERNAME=YourBotName
# 2) start stack
docker compose up --build
cd backend && uv run alembic upgrade head && uv run python scripts/seed.py
# 3) frontend
cd frontend && npm install && npm run dev  # http://localhost:5173
# 4) Settings → [Connect Telegram] → open bot → press Start → auto-connected ✅
#    (worker polls getUpdates every 30s, no chat-ID copy-paste; groups use manual fallback)
```

| URL | What |
|---|---|
| http://localhost:8000/health | Health check (db + redis) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000 | API info |

Demo login (after seeding): `demo@pulsetrack.dev` / `Demo1234!`
Frontend: Dashboard at `/` (LIVE badge = WS connected), Incidents at `/incidents` (AI explain + ack + ask), public status at `/s/{team-slug}` (no login), **Settings → Team + Telegram + Heartbeats + Keys + Webhooks + Maintenance + Audit**

### API (Phase 8: + CSV export; JWT bearer unless marked public)

```
POST   /api/v1/auth/register             {name, team_name, email, password} → tokens + user
POST   /api/v1/auth/login                {email, password}                  → tokens + user
POST   /api/v1/auth/refresh              {refresh_token}                    → new pair (rotated; reuse revokes all)
POST   /api/v1/auth/logout               (Bearer)                           → blacklist
GET    /api/v1/auth/me                   (Bearer)                           → user + team
GET    /api/v1/teams/me                  (Bearer)                           → team + plan
PUT    /api/v1/teams/me                  (Owner)                            → rename
GET    /api/v1/teams/members             (Bearer)                           → members
POST   /api/v1/teams/invite              (Owner) {email,role}               → add (temp password once)
DELETE /api/v1/teams/members/{id}        (Owner)                             → remove (not self)
POST   /api/v1/monitors                  (Member+)                          → create
GET    /api/v1/monitors                  (Bearer)                           → list + live status
GET    /api/v1/monitors/{id}             (Bearer)                           → detail + last checks
PUT    /api/v1/monitors/{id}             (Member+)                          → update
DELETE /api/v1/monitors/{id}             (Owner)                            → delete
POST   /api/v1/monitors/{id}/pause       (Member+)                          → pause
POST   /api/v1/monitors/{id}/resume      (Member+)                          → resume
GET    /api/v1/monitors/{id}/checks      (Bearer) ?page&limit&from&to       → checks page
GET    /api/v1/monitors/{id}/stats       (Bearer) ?days                     → uptime + latency
GET    /api/v1/notification-channels     (Bearer)                           → telegram channels
POST   /api/v1/notification-channels     (Member+) {telegram_chat_id,label} → add (manual, groups)
POST   /api/v1/notification-channels/connect (Member+) {label?}             → one-time t.me link
GET    /api/v1/notification-channels/connect/{token}/status (Bearer)        → pending|connected|expired
DELETE /api/v1/notification-channels/connect/{token} (Member+)              → cancel link
DELETE /api/v1/notification-channels/{id}(Member+)                           → delete
POST   /api/v1/notification-channels/{id}/test (Member+)                     → send test ✅
GET    /api/v1/maintenance               (Bearer)                           → windows
POST   /api/v1/maintenance               (Member+) {monitor_id?,starts,ends}→ create
DELETE /api/v1/maintenance/{id}          (Member+)                           → cancel
GET    /api/v1/incidents                 (Bearer) ?status                    → incidents
GET    /api/v1/incidents/{id}            (Bearer)                           → detail
POST   /api/v1/incidents/{id}/acknowledge(Member+)                           → ack (stops escalation)
GET    /api/v1/incidents/by-monitor/{mid}(Bearer)                            → per-monitor
WS     /ws/monitors?token=<JWT>          (WS, team-scoped)                   → live check events
GET    /status/{slug}                    (public, cached 30s)                → team + monitors + overall
GET    /status/{slug}/incidents          (public, cached 30s)                → recent incidents
POST   /api/v1/heartbeats                (Member+) {name,period_min,grace}   → create (ping_key once)
GET    /api/v1/heartbeats                (Bearer)                            → list ALIVE/MISSING
DELETE /api/v1/heartbeats/{id}           (Member+)                           → delete
POST   /api/v1/heartbeats/{key}/ping     (public, key auth)                  → proof-of-life
POST   /api/v1/incidents/{id}/analyze   (Member+)                           → AI root-cause (cached 24h)
GET    /api/v1/incidents/{id}/analysis  (Bearer)                            → cached read (~50ms, $0)
POST   /api/v1/ai/ask                   (Member+) {question}                → Q&A over team history + SRE knowledge
POST   /api/v1/api-keys                 (Owner) {name}                     → mint pk_live_… (shown once)
GET    /api/v1/api-keys                 (Owner)                             → list prefixes
DELETE /api/v1/api-keys/{id}            (Owner)                             → revoke (instant 401)
POST   /api/v1/webhooks/outbound        (Member+) {url,secret?}            → add (secret auto-made)
GET    /api/v1/webhooks/outbound        (Bearer)                            → list (no secrets)
POST   /api/v1/webhooks/outbound/{id}/test (Member+)                       → sample signed delivery
DELETE /api/v1/webhooks/outbound/{id}   (Member+)                           → remove
GET    /api/v1/audit-logs               (Owner) ?user&action&page&limit    → who did what
GET    /api/v1/monitors/{id}/checks/export (Bearer) ?from&to             → checks CSV (streamed, 50k cap)
GET    /api/v1/incidents/export         (Bearer) ?status                  → incidents CSV (streamed, 50k cap)
```

CSV opens straight in Excel/Sheets (Dashboard row button + Incidents Export button).
Tests: `cd backend && uv run pytest -q` (**112 tests**, needs Docker Postgres/Redis running);
coverage `uv run pytest --cov=app -q` → **88%** (`ruff` clean; config in `pyproject.toml`).

API keys work anywhere JWT does: `Authorization: Bearer pk_live_…` (inherits creator's role).
Webhooks POST HMAC-signed JSON (`X-Signature`, `X-Timestamp`) on incident OPEN/RECOVERY.

```bash
# machine usage (CI/cron) — create once, reuse the key
KEY=$(curl -s -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $JWT" -H 'Content-Type: application/json' \
  -d '{"name":"ci"}' | python -c "import sys,json; print(json.load(sys.stdin)['data']['key'])")
curl -s -X POST http://localhost:8000/api/v1/monitors \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"name":"Shop","url":"https://example.com","interval_min":5}'

# verify a webhook delivery (receiver side, Python)
import hmac, hashlib, time
def valid(secret, ts, body, sig):
    if abs(time.time() - ts) > 300: return False
    expect = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expect, sig)
```

Telegram auto-connect (Option A — polling, 100% free): `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME` from @BotFather. Settings → [Connect Telegram] → backend creates one-time token (Redis, 15 min TTL) → `t.me/Bot?start=TOKEN` → user presses Start → worker `poll_telegram_updates` cron (every 30s, `getUpdates`) auto-creates the channel + sends ✅. No chat-ID copy-paste (groups still use manual fallback). Alerts: OPEN → Telegram, RESOLVED → recovery, 10m unacked → escalation. Muted when in maintenance window. Retries 3×, all logged in `alert_logs`.

Deploy: backend api + ARQ worker on **Northflank Sandbox** (2 always-on services free, no 15-min sleep), frontend on Vercel, Postgres on Neon (free, permanent), Redis on Upstash (free, persistent). Same Docker image for api (`uvicorn`) + worker (`arq`).

Live: worker publishes every finished check to Redis pub/sub `live`; Dashboard WS patches dots instantly (30s polling stays as fallback). Heartbeat checker cron runs every minute: silence past period+grace → MISSING + Telegram (💔/💚), idempotent, logged in `alert_logs` (kind open/recovery, no incident row in v1).

AI analyst (Phase 6): free `GEMINI_API_KEY` from [AI Studio](https://aistudio.google.com/apikey) (+ optional `GEMINI_MODEL`, default `gemini-3.5-flash-lite` — `gemini-2.0-flash` is retired). Cache-first: repeat Explains cost $0 (Redis 24h + `incidents.ai_summary`); prompts use last 20 checks only; 10/min/user rate-limit; 429/timeout → graceful "AI busy", never breaks incidents.

Quality (Phase 8): **112 tests, 88% coverage**, `ruff` clean. New code is covered by
`tests/test_telegram_flow.py`, `test_status_live.py`, `test_alerts.py`,
`test_heartbeats.py`, `test_export.py`, `test_flows.py` (CSV, ack, maintenance, health).

Stop: `docker compose down` (add `-v` to wipe the database volume).

## Layout

```
backend/            FastAPI app (app/main.py, app/core/config.py)
docker-compose.yml  api + postgres + redis
frontend/           React SPA (from Phase 2)
PROGRESS_LOG.md     step-by-step build diary (read this first)
```
