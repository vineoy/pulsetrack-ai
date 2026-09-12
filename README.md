# PulseTrack AI

Uptime monitoring + public status page SaaS with an **AI incident analyst** (Gemini).
Add a URL → workers ping it every minute → outages open incidents automatically →
alerts fire (email / Discord / Telegram) → AI explains the root cause → customers see a
public status page. Full plan: `PulseTrack-AI-Roadmap.pdf`. Progress: `PROGRESS_LOG.md`.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL 16 · Redis 7 · ARQ workers ·
React + TS + Vite (Phase 2+) · Gemini 2.0 Flash · uv · Docker · GitHub Actions · Render + Vercel (free tier, $0/month)

## Run locally (Phase 1 state)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) running, [uv](https://docs.astral.sh/uv/) installed.

```bash
docker compose up --build
cd backend && uv run alembic upgrade head && uv run python scripts/seed.py
```

| URL | What |
|---|---|
| http://localhost:8000/health | Health check (db + redis) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000 | API info |

Demo login (after seeding): `demo@pulsetrack.dev` / `Demo1234!`

### API (Phase 1: auth + teams, JWT bearer)

```
POST /api/v1/auth/register   {name, team_name, email, password} → tokens + user
POST /api/v1/auth/login      {email, password}                  → tokens + user
POST /api/v1/auth/refresh    {refresh_token}                    → new token pair (rotated; reuse revokes all sessions)
POST /api/v1/auth/logout     (Bearer)                           → blacklists access token
GET  /api/v1/auth/me         (Bearer)                           → user + team
GET  /api/v1/teams/me        (Bearer)                           → team detail + member count
PUT  /api/v1/teams/me        (Owner) {name?, slug?}             → rename / change status slug
GET  /api/v1/teams/members   (Bearer)                           → member list
POST /api/v1/teams/invite    (Owner) {email, role}              → add member, returns one-time temp password
```

Tests: `cd backend && uv run pytest -q` (16 tests, needs Docker Postgres/Redis running)

Stop: `docker compose down` (add `-v` to wipe the database volume).

## Layout

```
backend/            FastAPI app (app/main.py, app/core/config.py)
docker-compose.yml  api + postgres + redis
frontend/           React SPA (from Phase 2)
PROGRESS_LOG.md     step-by-step build diary (read this first)
```
