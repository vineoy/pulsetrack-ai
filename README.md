# PulseTrack AI

Uptime monitoring + public status page SaaS with an **AI incident analyst** (Gemini).
Add a URL → workers ping it every minute → outages open incidents automatically →
alerts fire (email / Discord / Telegram) → AI explains the root cause → customers see a
public status page. Full plan: `PulseTrack-AI-Roadmap.pdf`. Progress: `PROGRESS_LOG.md`.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL 16 · Redis 7 · ARQ workers ·
React + TS + Vite (Phase 2+) · Gemini 2.0 Flash · uv · Docker · GitHub Actions · Render + Vercel (free tier, $0/month)

## Run locally (Phase 0 state)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) running, [uv](https://docs.astral.sh/uv/) installed.

```bash
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8000/health | Health check (db + redis) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000 | API info |

Stop: `docker compose down` (add `-v` to wipe the database volume).

## Layout

```
backend/            FastAPI app (app/main.py, app/core/config.py)
docker-compose.yml  api + postgres + redis
frontend/           React SPA (from Phase 2)
PROGRESS_LOG.md     step-by-step build diary (read this first)
```
