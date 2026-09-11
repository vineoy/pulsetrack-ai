# PulseTrack AI — Master Progress Log

> This file is the single source of truth for everything we have done on this project.
> Every action (command run, file created, decision made, error hit and fixed) is recorded here
> step by step, newest phase at the bottom. Never delete old entries — this is our project diary.

---

## Project Snapshot

| Item | Value |
|---|---|
| Project | PulseTrack AI — Uptime Monitoring + Status Page SaaS with AI Incident Analyst |
| Full plan | `PulseTrack-AI-Roadmap.pdf` / `generate_roadmap_pdf.py` (17 locked features, Phases 0–10) |
| Stack | Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, uv, PostgreSQL 16, Redis 7, ARQ, React+TS, Gemini |
| Repository | Local git repo, branch `main` |
| Log started | 2026-09-12 |

## Phase Status

| Phase | Name | Status | Date completed |
|---|---|---|---|
| 0 | Setup + Docker hello | ✅ DONE | 2026-09-12 |
| 1 | Auth + Teams + RBAC | ⬜ not started | — |
| 2 | Monitors + Checks read | ⬜ not started | — |
| 3 | Real Worker + Scheduler | ⬜ not started | — |
| 4 | Alerts + Escalation + Maintenance | ⬜ not started | — |
| 5 | Live WS + Public Page + Heartbeat | ⬜ not started | — |
| 6 | Gemini AI | ⬜ not started | — |
| 7 | API Keys + Webhooks + Audit | ⬜ not started | — |
| 8 | Testing + Polish + CSV Export | ⬜ not started | — |
| 9 | Docker prod + CI/CD | ⬜ not started | — |
| 10 | Launch + Portfolio | ⬜ not started | — |

## Developer Environment (as detected on this machine)

| Tool | Version | Status |
|---|---|---|
| uv | 0.12.9 | ✅ installed |
| git | 2.47.1.windows.2 | ✅ installed (user: vinayak / singhvinayak288@gmail.com) |
| Docker Engine | 27.5.1 | ✅ running |
| Docker Compose | v2.32.4-desktop.1 | ✅ installed |
| GitHub remote | — | ⬜ not created yet (pending: user creates repo or `gh auth login`) |

---

# PHASE 0 — Setup + Docker Hello (COMPLETED 2026-09-12)

**Goal (from roadmap):** `uv init`, Docker Compose with api (hot reload) + Postgres 16 + Redis 7,
`GET /health` returns ok, `/docs` opens, first git commit.

**Done = ✅ VERIFIED:** `docker compose up` works, `/health` → 200 `{"status":"ok","db":"up","redis":"up"}`, `/docs` → 200.

## Step-by-step actions performed

### 0.1 — Prerequisite checks
- Ran `uv --version` → `uv 0.12.9` ✅
- Ran `git --version` → `2.47.1.windows.2`, global user.name/email configured ✅
- Ran `docker --version` / `docker info` → Docker 27.5.1, daemon running ✅
- Result: no installations needed, proceeded.

### 0.2 — Project skeleton created (14 files, all hand-written)
| File | Purpose |
|---|---|
| `.gitignore` | keeps venv, caches, `.env` secrets, node_modules out of git |
| `.gitattributes` | consistent line endings (LF in repo, CRLF safe on Windows) |
| `docker-compose.yml` | defines 3 services: `db` (postgres:16-alpine), `redis` (redis:7-alpine), `api` (our FastAPI, hot reload). db+redis have healthchecks; api uses `depends_on: condition: service_healthy` so it only starts after they are ready. Named volume `pgdata` survives restarts. |
| `backend/pyproject.toml` | dependency list (fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, redis, arq, httpx) + dev group (pytest, pytest-asyncio, ruff) + ruff config |
| `backend/.python-version` | pins Python 3.12 |
| `backend/Dockerfile` | dev image: python:3.12-slim + uv; venv at `/opt/venv` (OUTSIDE `/app` so the volume mount never shadows it); dependency layer cached separately from code layer |
| `backend/.dockerignore` | keeps `.venv`, caches, `.env` out of the image build |
| `backend/.env.example` | template of all env vars; real `.env` is git-ignored |
| `backend/app/__init__.py`, `backend/app/core/__init__.py` | make `app` a Python package |
| `backend/app/core/config.py` | `Settings` (pydantic-settings): reads env vars case-insensitively, `.env` file support, `@lru_cache` singleton `get_settings()`. Declares DATABASE_URL, REDIS_URL, JWT/GEMini/RESEND placeholders for later phases |
| `backend/app/main.py` | FastAPI app factory-less minimal app: `lifespan` closes DB pool + Redis on shutdown; `GET /` info; `GET /health` runs `SELECT 1` on Postgres + `PING` on Redis, returns 200 `ok` or 503 `degraded` |
| `.vscode/settings.json` | VS Code: interpreter = `backend/.venv`, format-on-save with Ruff |
| `.vscode/extensions.json` | recommends Python + Ruff extensions |

### 0.3 — Dependencies installed (host, for VS Code IntelliSense)
- Command: `uv sync --directory backend`
- Result: created `backend/.venv` + `uv.lock` (exact pinned versions, e.g. fastapi, pydantic 2.13.5, sqlalchemy 2.0.52, redis 5.3.1, uvicorn 0.52.4) ✅

### 0.4 — Git initialized
- Command: `git init -b main` → `git add -A` → `git commit`
- Commit 1: `Phase 0: project skeleton - FastAPI app, Docker Compose (api+db+redis), uv, /health endpoint`
- Note: CRLF warnings on Windows are normal, `.gitattributes` handles it. ✅

### 0.5 — Stack built & started
- Command: `docker compose up -d --build`
- Pulled `python:3.12-slim`, `postgres:16-alpine`, `redis:7-alpine`, copied uv binary from `ghcr.io/astral-sh/uv`, ran `uv sync --frozen` inside image.
- Startup order observed: db+redis started → healthchecks polled (`pg_isready`, `redis-cli ping`) → marked Healthy → only then api started. ✅

### 0.6 — Verification (roadmap "Done" checklist)
| Check | Command | Result |
|---|---|---|
| API health | `curl http://localhost:8000/health` | `200 {"status":"ok","db":"up","redis":"up"}` ✅ |
| Swagger docs | `curl -o /dev/null -w "%{http_code}" .../docs` | `200` ✅ |
| Root info | `curl http://localhost:8000/` | `{"app":"PulseTrack AI","docs":"/docs","health":"/health"}` ✅ |
| Containers | `docker compose ps` | api Up, db Up (healthy), redis Up (healthy) ✅ |

## Decisions made in Phase 0
1. **Project layout**: `backend/` + `frontend/` (from Phase 2) side by side, compose file at root.
2. **Docker venv outside mount**: `UV_PROJECT_ENVIRONMENT=/opt/venv` — otherwise the `./backend:/app` volume mount would hide the image's venv (classic Windows Docker gotcha).
3. **Simple dev Dockerfile now**, multi-stage + non-root + healthcheck in Phase 9 (per roadmap).
4. **Hardcoded local-only dev creds** (`pulse:pulse`) inside compose; real secrets only ever in `.env` / cloud env vars.
5. **api command in compose overrides Dockerfile CMD** to add `--reload` (hot reload) — dev only.

## Current state of the system
- Stack is RUNNING: API on http://localhost:8000 (docs at /docs), Postgres on localhost:5432 (db: pulsetrack, user: pulse), Redis on localhost:6379.
- Stop with `docker compose down` (add `-v` to also wipe database data).
- Hot reload is ON: editing any file under `backend/` restarts the API automatically.
- No database tables yet — Alembic + first migration arrive in Phase 1.

## Next: Phase 1 — Auth + Teams + RBAC
Models teams/users + Alembic migration 001, bcrypt hashing, JWT access 15m / refresh 7d with
rotation + reuse detection, Redis blacklist for logout, `require_role` dependency, 8 pytest tests,
audit logging of auth events.

---
*Log maintained by the build agent; updated after every action. Last update: 2026-09-12 (Phase 0 complete).*
