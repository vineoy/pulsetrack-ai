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
| 1 | Auth + Teams + RBAC | ✅ DONE | 2026-09-12 |
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

## Next: Phase 2 — Monitors + Checks Read

---
*Log maintained by the build agent; updated after every action. Last update: 2026-09-12 (Phase 1 complete).*

---

# PHASE 1 — Auth + Teams + RBAC (COMPLETED 2026-09-12)

**Goal (from roadmap):** Models teams/users + Alembic migration 001, bcrypt hashing, JWT 15m/7d
with rotation + reuse detection, Redis blacklist on logout, `require_role` dependency, 8+ pytest
tests, audit logging of auth events.

**Done = ✅ VERIFIED:** 16/16 tests green, ruff clean, live smoke test of the full security
lifecycle against the Docker stack passed, audit trail confirmed in Postgres.

## What was built (3 endpoints over plan: +refresh, +members, +invite)

| Layer | Files | What it does |
|---|---|---|
| Models | `app/models/{base,enums,team,user,audit_log}.py` | Declarative Base with naming convention; UUID pk + timestamp mixins; `Team` (slug unique, plan), `User` (team FK CASCADE, role, bcrypt hash), `AuditLog` (SET NULL FKs — the log outlives deleted rows). StrEnum stored as lowercase VARCHAR (no native PG enum = free future values) |
| Core | `app/core/{db,redis,exceptions,security}.py` | async engine + session-per-request; Redis client; uniform error envelope `{data,error:{code,message}}` + handlers for AppError/HTTP/422; bcrypt cost 12; PyJWT HS256 encode/decode with typed payload (sub, jti, type, team_id, role, iat, exp) |
| Schemas | `app/schemas/{common,auth,team}.py` | PEP 695 generic `ApiResponse[T]`; RegisterIn/LoginIn (email normalize, password ≤72 bytes — bcrypt silently truncates beyond that); TokenPayload; TeamUpdateIn slug regex; InviteIn/InviteOut (temp password shown once) |
| Repositories | `app/repositories/{user,team,audit}_repository.py` | All SQL lives here; services never touch Session query APIs directly |
| Services | `app/services/{auth,team}_service.py` | Business logic: register (team+owner in one tx), login (identical error for unknown email vs wrong password), refresh rotation w/ reuse detection, logout blacklist, slug generation w/ collision suffix, invite member |
| API | `app/api/deps.py`, `app/api/v1/routers/{auth,teams}.py` | 9 endpoints (5 auth + 4 teams); `CurrentUser`, `OwnerUser`, `MemberUser` role dependencies; token-type check + Redis blacklist check in `get_current_user` |
| Migration | `migrations/versions/0d3786a49620_…py` + wired `env.py` | Autogenerated 001 from models; URL from settings; `compare_type=True` |
| Tests | `tests/{conftest,test_auth,test_teams}.py` | 16 tests: register/login/me, dup email 409, short password 422, wrong-password 401, identical unknown-email error, no-token 401, refresh rotation → reuse → family revocation, access-as-refresh 401, logout blacklist, viewer-invite 403, team rename/slug-conflict/members list. Isolation: dedicated `pulsetrack_test` DB (schema dropped/recreated per test) + Redis DB 1, via dependency_overrides |
| Seed | `scripts/seed.py` | demo-team / demo@pulsetrack.dev / Demo1234! (idempotent) |

## Step-by-step actions (with every error hit)

1. `uv add bcrypt pyjwt "pydantic[email]"` + `uv run alembic init -t async migrations` ✅
2. Wired `migrations/env.py` (settings URL + `Base.metadata`), added pytest config to pyproject ✅
3. Wrote all layers above (models → core → schemas → repos → services → routers → main) ✅
4. **BUG #1 (environment):** `alembic revision --autogenerate` → `InvalidPasswordError for user "pulse"`.
   Diagnosis: `netstat -ano` showed TWO listeners on 5432 — Docker's proxy AND a local Windows
   PostgreSQL service (`postgres.exe` PID 6944). Host tools were silently hitting the local PG.
   **Fix:** moved container host port to **5433** (compose `"5433:5432"`, config default,
   conftest, .env.example). In-Docker traffic (`db:5432`) unchanged. Lesson: verify which
   process owns a port before assuming your container is the target.
5. **BUG #2 (lint):** ruff found 8 issues → auto-fixed imports; manually migrated to
   `enum.StrEnum` + PEP 695 generics + wrapped one long line. Ruff clean ✅
6. Autogenerated migration 001 (teams/users/audit_logs + all indexes/constraints), applied via
   `alembic upgrade head` ✅
7. **BUG #3 (tests):** 15/16 ERROR — SQLAlchemy wraps asyncpg's `DuplicateDatabaseError` in its
   own `ProgrammingError`, so the except never matched. **Fix:** check `pg_database` first, create
   only if missing (AUTOCOMMIT — CREATE DATABASE can't run in a transaction). → **16/16 passed** ✅
8. **Warning fixed:** pyjwt flagged dev JWT secret < 32 bytes (RFC 7518). Longer dev default; prod
   injects real secret via env ✅
9. `docker compose up -d --build` (new image with auth code) + migration + seed ✅
10. **Live smoke test vs Docker stack (all passed):**
    - register → 201 with tokens; `/auth/me` with token → user+team; without token → `NOT_AUTHENTICATED`
    - refresh → rotated (different token); replay old refresh → `REFRESH_REUSE_DETECTED`;
      legitimately-rotated sibling → also dead (family revocation works)
    - logout → access token now `TOKEN_REVOKED` (Redis blacklist)
    - viewer tries to invite → 403 `FORBIDDEN`
    - `audit_logs` table shows: auth.register(2), auth.login(2), auth.refresh(1),
      auth.refresh_reuse_detected(2), auth.logout(1), team.member_invited(1) ✅
11. Updated README (endpoints + demo creds), committed in 2 commits.

## Decisions made in Phase 1
1. **Layered architecture** (router → service → repository → model): routers stay thin,
   business logic testable without HTTP, all SQL in one layer. Seniors expect this.
2. **Opaque refresh tokens in Redis** (key = `refresh:{user_id}:{jti}`): refresh validity is a
   Redis lookup, so rotation/revocation/family-kill is instant and stateful; JWT only proves
   identity for the short-lived access token.
3. **Reuse detection revokes the whole family** — stolen-token signal (industry best practice).
4. **Audit `user_id/team_id` SET NULL**: logs outlive deleted users/teams.
5. **Same error message for unknown email and wrong password** (no user enumeration).
6. **No native PG enums** (VARCHAR + values_callable): adding a role later needs no migration.
7. **Container port moved to 5433** instead of fighting the machine's local PostgreSQL service.
8. **Invites in v1 = direct add with a one-time temp password** (email invites = v2).

## Current state
- 9 endpoints live under `/api/v1` (auth 5, teams 4) — see http://localhost:8000/docs
- Tables: teams, users, audit_logs (+ `alembic_version`). Demo login seeded.
- Test DB `pulsetrack_test` + Redis DB 1 are test-only and safe to wipe.
- 16 tests · ruff clean · 4 commits on `main`.

## Next: Phase 2 — Monitors CRUD + Checks Read
Monitors/checks models + migration 002 (BRIN index prep), 7 monitor endpoints + checks/stats
reads, 10-monitors free-plan limit, URL validation, caching basics, dashboard-ready data,
+ frontend boot (React+Vite) with login + monitor table.

