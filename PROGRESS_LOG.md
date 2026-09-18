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
| 2 | Monitors + Checks read | ✅ DONE | 2026-09-13 |
| 3 | Real Worker + Scheduler | ✅ DONE | 2026-09-15 |
| 4 | Alerts (Telegram-only) + Escalation + Maintenance + UI/UX Polish + Telegram auto-connect | ✅ DONE | 2026-09-17 |
| 5 | Live WS + Public Page + Heartbeat | ✅ DONE | 2026-09-17 |
| 6 | Gemini AI (+draft removal + Ask general knowledge) | ✅ DONE | 2026-09-18 |
| 7 | API Keys + Webhooks + Audit + Team invites UI | ✅ DONE | 2026-09-18 |
| 8 | Testing + Polish + CSV Export | ✅ DONE | 2026-09-18 |
| 9 | Docker prod + CI/CD | ✅ DONE | 2026-09-18 |
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
*Log maintained by the build agent; updated after every action. Last update: 2026-09-13 (Phase 2 complete).*

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

## Next: Phase 3 — Real Worker + Scheduler
Worker pings URLs every minute (ARQ + httpx), keyword/SSL asserts, flap logic
(2x DOWN → OPEN incident, 2x UP → RESOLVED), `next_check_at` scheduling loop.

---

# PHASE 2 — Monitors + Checks Read (COMPLETED 2026-09-13)

**Goal (from roadmap):** Models monitors/checks + migration 002, 7 monitor endpoints +
checks/stats reads (mock/fake data first, real worker comes in Phase 3), 10-monitors
free-plan limit, URL validation, dashboard-ready data + frontend boot (React+Vite)
with login + monitor table.

**Done = ✅ VERIFIED:** 31/31 tests green (16 Phase-1 + 15 Phase-2), ruff clean on
`app/tests/scripts`, Alembic at head `b50beb9eaf3f` (002), Docker rebuilt + `/health`
`ok` + `/docs` 200, live smoke test of full monitor lifecycle passed, frontend
`tsc -b + vite build` green.

## What was built (9 backend endpoints + React dashboard)

| Layer | Files | What it does |
|---|---|---|
| Models | `app/models/monitor.py`, `app/models/check.py` | `Monitor` (team FK CASCADE, name/url/method/interval 1-5-10-30 via DB CheckConstraint, keyword≤200, ssl_check, is_paused, `next_check_at` for Phase-3 scheduler) + `Check` (append-only probe result: status UP/DOWN, latency_ms, status_code, error, checked_at; composite index `(monitor_id, checked_at)` + BRIN on `checked_at` for the huge time-series table) |
| Schemas | `app/schemas/monitor.py` | `MonitorIn` (HttpUrl rejects `not-a-url` with 422 before DB; Literal interval; keyword strip), `MonitorUpdateIn`, `MonitorOut`, `MonitorSummaryOut` (+current_status/last_latency/last_checked for dashboard rows), `CheckOut`, `CheckPage` (paginated), `StatsOut` (uptime %, avg/p50/p95, last_checked) |
| Repositories | `app/repositories/monitor_repository.py`, `app/repositories/check_repository.py` | All SQL here: team list/count, `stats()` via `count/filter/avg/percentile_cont/max` (single query), checks paging with from/to filters + newest-first, `latest_per_monitor` via one Postgres `DISTINCT ON` query (no N+1 for dashboard), `recent_for_monitor(20)` |
| Services | `app/services/monitor_service.py` | Business rules: free-plan 10-monitor cap → 403 `PLAN_LIMIT_REACHED`; tenancy guard `_owned_monitor` → 404 (not 403) for other teams' ids; create sets `next_check_at=now` (scheduler-ready); update resets `next_check_at` on url/interval change; pause/resume; stats math (`up/total*100`, p50/p95, 0.0 on empty); audit `monitor.created/updated/deleted/paused/resumed` on every write |
| API | `app/api/v1/routers/monitors.py` (+ wired in `api/v1/__init__.py`) | 9 endpoints: POST/GET list/GET detail/PUT/DELETE (owner-only)/POST pause/POST resume/GET checks (page/limit≤500 + ?from&to)/GET stats (?days 1–90). RBAC: create/update/pause/resume = MemberUser (owner+member), delete = OwnerUser, viewer = read-only |
| Migration | `migrations/versions/b50beb9eaf3f_002_monitors_checks.py` | Autogenerated 002 from models: `monitors` (FK teams CASCADE + interval constraint) + `checks` (FK monitors CASCADE + composite + BRIN indexes) |
| Tests | `tests/test_monitors.py` | 15 tests: create+detail, bad URL 422, bad interval 422, update, pause/resume, owner delete + 404 after, 11th-monitor 403, viewer-create 403, cross-team 404 (not 403), list isolation, checks pagination (75 rows → total 75, 50 items, newest-first), stats math (3 UP + 1 DOWN → 75.0%, avg 200.0, p50 200.0, p95 290.0), empty stats 0.0, dashboard UP row, paused row |
| Seed | `scripts/seed.py` | Extended: demo-team + 3 monitors + ~181 fake checks each (3h of 1-min probes with a 10-min DOWN outage window) so dashboard/stats have data before Phase-3 worker |
| Frontend | `frontend/` (Vite+React19+TS+Tailwind4+Query+Router+axios) | `lib/api.ts` (axios base `/api/v1`, token attach, 401→refresh-once→retry, unwrap `{data,error}` envelope), `types.ts` (MonitorSummary/CheckOut/StatsOut), `pages/Login.tsx` (login/register tabs, demo creds hint), `pages/Dashboard.tsx` (stat cards Up/Down/Paused, +Add form 1/5/10/30, table with green/red/amber/grey dots, pause/resume, owner-only delete, 30s auto-refetch), `vite.config.ts` (dev proxy `/api` → localhost:8000, no CORS), `App.tsx` (protected `/` route) |

## Step-by-step actions performed

1. Inspected repo state: `git log` (Phase 0+1 committed) + `git status` showed Phase-2
   files already drafted in working tree but uncommitted (models, schemas, repos,
   service, router, migration 002, tests, frontend, seed extension). Goal of this
   session: verify everything end-to-end, wire up Docker, smoke-test live, log it. ✅
2. Read all Phase-2 files (models, schemas, service, router, repos, migration, tests,
   seed diff, frontend App/Login/Dashboard/api-client/types/vite config) to confirm
   they match roadmap (7 monitor endpoints + checks/stats + 10-limit + audit). ✅
3. Ran `uv run pytest -q` in `backend/` → **31 passed in ~20s** (16 auth/teams + 15
   monitors). No failures. ✅
4. Ran `uv run ruff check app tests scripts` → **All checks passed**. (Note: bare
   `ruff check .` flags 29 issues inside `migrations/` autogenerated files — same as
   Phase 1; migrations are Alembic-generated, excluded from the clean verdict.) ✅
5. Ran `uv run alembic upgrade head` → already at head `b50beb9eaf3f` (002); `alembic
   current` confirms. Dev DB has monitors+checks tables. ✅
6. Rebuilt stack: `docker compose up -d --build` (api image was 1h stale on Phase-1
   code) → api recreated, db+redis healthy, api Up on :8000. ✅
7. Verified `/health` → `{"status":"ok","db":"up","redis":"up"}` and `/docs` → 200. ✅
8. **Live smoke test vs Docker stack (all passed):** register → 201; create monitor →
   201; list → 1 row; detail → uptime `None` (no checks yet, correct); stats → 0
   checks/0.0%; checks page → total 0; pause → `is_paused True` + list shows `PAUSED`;
   resume → False; bad URL → 422 `VALIDATION_ERROR`; delete → 200; get-after-delete
   → 404. ✅
9. Frontend: `npm run build` → `tsc -b + vite build` green (144 modules, dist emitted).
   `npm run lint` (oxlint) initially failed with missing native binding
   (`@oxlint/binding-win32-x64-msvc`) — root cause: oxlint ≥1.17 requires Node
   `^20.19 || >=22.12` but the machine ran Node v20.13.1, so npm silently skipped
   the optional native binding and NO reinstall could fix it. Temporary fix was
   pinning oxlint to 1.16.0.
   **Permanent fix (2026-09-13):** upgraded system Node 20.13.1 → **24.19.0 LTS**
   via `winget install OpenJS.NodeJS.LTS` (user approved the UAC prompt; first
   attempt hung at UAC as orphan msiexec PID 3856 which could not be killed
   without admin — second attempt after user confirmation succeeded). Then
   unpinned oxlint back to latest (`^1.82.0`, binding installs correctly now) and
   locked the floor for the future: `frontend/.nvmrc` = 24 + `"engines":
   {"node": ">=20.19"}` in `package.json` (advisory, never blocks installs).
   Final state: lint 0 warnings/0 errors (116 rules), build output byte-identical
   (367.91 kB bundle), backend 31/31 still green — zero app behavior change. ✅
10. Updated this log (phase table → DONE 2026-09-13 + this diary). README endpoint-table
    + commit still pending — awaiting user go-ahead per commit policy.

## Decisions made in Phase 2
1. **Checks table is append-only + indexed for scale**: composite `(monitor_id,
   checked_at)` for per-monitor time graphs, BRIN on `checked_at` (tiny index, ideal
   for ever-growing timestamp data). Mention in interviews.
2. **Dashboard list avoids N+1** via single `DISTINCT ON (monitor_id)` query for latest
   checks; stats via single aggregate query (`percentile_cont` for p50/p95 in SQL).
3. **404 — never 403 — for cross-team monitor ids** (no existence leak), same tenancy
   philosophy as Phase 1.
4. **Free-plan cap enforced in service layer** (`PLAN_LIMITS` map; pro = unlimited by
   absence) → 403 `PLAN_LIMIT_REACHED`; easy to extend per-plan later.
5. **Fake seed data (not live pings)** until Phase 3: API only reads data; worker will
   write it. Keeps layers honest.
6. **Viewer is read-only** (MemberUser = owner+member for writes; OwnerUser for delete).
7. **Ruff clean verdict scopes to hand-written code** (`app tests scripts`); Alembic
   autogenerated files are left as-generated.

## Current state
- 18 endpoints live under `/api/v1` (9 auth/teams from Phase 1 + 9 monitors/checks/stats).
- Tables: teams, users, audit_logs, monitors, checks (+ `alembic_version` = 002).
- Tests: 31 green · ruff (hand-written) clean · Docker stack RUNNING with Phase-2 code.
- Frontend boots: login/register → dashboard table + add/pause/resume/delete, 30s refresh.
- Lint: `npm run lint` green (oxlint latest + native binding; Node 24 LTS; floor locked via `.nvmrc` + `engines`).
- Uncommitted work: all Phase-2 files listed above + `frontend/package.json` /
  `package-lock.json` (oxlint pin) (commit on user approval).

## Next: Phase 3 — Real Worker + Scheduler


---

# PHASE 3 — Real Worker + Scheduler + Flap Logic (COMPLETED 2026-09-15)

**Goal (roadmap):** ARQ scheduler cron 30s + check_job with httpx 10s timeout; keyword/SSL asserts;
Redis lock per monitor; flap logic 2x DOWN → OPEN / 2x UP → RESOLVED + downtime_sec.
**Done = ✅ VERIFIED:** live test — dead-URL monitor produced DOWN checks every minute and an
incident row appeared automatically after the 2nd failure; all monitors on 1/5/10-min schedules
are being probed for real; 47/47 tests green; ruff clean.

## What was built

| File | What it does |
|---|---|
| `app/models/incident.py` + migration `9e741a0e50d1` | `incidents` table (monitor_id, team_id, status OPEN/ACK/RESOLVED as String(10)+CHECK constraint, started_at, ack_at, resolved_at, downtime_sec, ai_summary placeholder for Phase 6). Indexes: (monitor_id,status) hot lookup + (team_id,started_at) history |
| `app/services/incident_service.py` | `apply_flap_logic`: 2 consecutive DOWN + no OPEN → create; 2 consecutive UP + OPEN → RESOLVE with downtime_sec = resolved_at - started_at; **idempotent** (never two incidents for the same outage); single DOWN or flapping DOWN/UP/DOWN opens nothing |
| `app/workers/checker.py` | `check_job(ctx, monitor_id)`: Redis lock `lock:monitor:{id}` NX EX 60 (loser returns `skipped:locked`) → probe (httpx 10s, follow redirects, UA header; exceptions → DOWN, never crash) → save Check → `next_check_at = now + interval` → flap logic → commit → release lock. `decide_outcome()` is a pure function (unit-tested): 2xx/3xx + keyword ⇒ UP. `enqueue_due_monitors`: SELECT due, not paused → enqueue (limit 500) |
| `app/workers/settings.py` | ARQ `WorkerSettings`: functions=[check_job], cron every 30s (`second={0,30}`, unique), job_timeout 45s, max_jobs 20, max_tries 4 |
| `docker-compose.yml` | new `worker` service: same image, command `arq app.workers.settings.WorkerSettings`, hot-reload via same volume mount |
| `tests/test_worker.py` (16 tests) | decide_outcome truth table (2xx/3xx/4xx/5xx/keyword), check_job with `httpx.MockTransport` (UP saved, DOWN on ConnectError, keyword-miss DOWN, rescheduling, garbage id raises, lock → skipped:locked + no check written), flap logic (exactly one incident, idempotency, resolve+downtime bounds, single/flapping patterns), scheduler query (due found, paused skipped, NULL next_check_at never due) |

## Step-by-step + errors hit
1. Incident model written; first attempt used `SAEnum(("OPEN",...))` — **BUG: passing plain strings
   to SAEnum is invalid** (KeyError 'OPEN' at query time). Fix: `String(10)` + CHECK constraint.
2. Deleted the bad autogenerated migration → alembic couldn't resolve its version id
   (`Can't locate revision 7980e737bd96`); `alembic stamp` also failed → fixed by updating
   `alembic_version` row directly via psql, then regenerated 003. Lesson: delete migrations only
   after downgrade, or repair the version table.
3. Worker wired into compose; `--build` recreated api+worker. Worker log confirmed: cron fired →
   enqueued → `check_job` ran.
4. **Live "Done" test:** created monitor `https://nonexistent-domain-qz948.dev` (1-min) →
   checks appeared DOWN (`http error: ConnectError`) at :45:00 and :46:31 →
   `incidents` table gained `OPEN / Dead Target` automatically after the 2nd failure. ✅
5. **BUG (found live):** seeded monitors had `next_check_at = NULL` → never enqueued
   (`NULL <= now` is never true in SQL). Fixed seed script (+ regression test documenting the
   semantics) and woke existing rows with an UPDATE. All 5 monitors now check on schedule.
6. Test-file import nits (UTC vs timezone alias, F821s) — fixed; ruff clean, **47/47 green**.
7. Committed `220410c`.

## Decisions made in Phase 3
1. **Status column as String + CHECK**, not SAEnum — plain strings compare everywhere and
   adding a value later needs no migration.
2. **Lock-then-check with NX+EX** — crash-safe (TTL auto-releases); loser skips silently.
3. **check retries = 0 by design** — the next 30s scheduler tick is the retry; no poison-pill jobs.
4. **`decide_outcome` pure function** — the whole truth table is unit-testable without network.
5. **Worker shares the api image** (`command` differs) — one build, two roles; prod (Phase 9)
   will run them as separate services.
6. **MockTransport injection** (`set_client_for_testing`) — worker tests run with zero real HTTP.
7. Flap logic reads only the **last 2 checks** — O(1) work per probe regardless of history size.

## Current state
- Stack RUNNING: api :8000, worker (ARQ), db, redis. Real checks accumulating every minute.
- Tables: teams, users, audit_logs, monitors, checks, incidents (migration 003).
- Demo data: 3 healthy seeded monitors + 1 dead target (OPEN incident) for the dashboard.
- 47 tests · ruff clean · 6 commits.

## Next: Phase 4 — Alerts (Telegram-only) + Escalation + Maintenance + UI/UX Polish
notification_channels(telegram) + alert_logs + maintenance_windows (migration 004),
Telegram Bot API sender with 3x retry/backoff, alert on OPEN/recovery on RESOLVED,
escalate if OPEN 10 min unacked, mute when in maintenance window, channels Test button
+ full dashboard UI/UX redesign (new header, cards, table, polish).

---

# PHASE 4 — Alerts (Telegram-only) + Escalation + Maintenance + UI/UX Polish (IN PROGRESS — started 2026-09-16)

**Goal (roadmap Phase 4 adapted per user request):** keep alerting **only via Telegram Bot**
(no email, no Discord/Slack), wire it to real incidents from Phase 3, add escalation &
maintenance mute, **and** make the frontend look production-grade. Old multi-channel code
will be deleted everywhere.

**Scope locked for Phase 4:**
- Backend: `notification_channels` (telegram-only), `alert_logs`, `maintenance_windows`
  + migration 004, Telegram sender (Bot API), alert on OPEN / recovery on RESOLVED,
  escalation after 10 min if still OPEN+unacked, maintenance-window skip, `POST /notification-channels/{id}/test`.
- Frontend: UI/UX redesign — see detailed plan above (header, stat cards, monitor table/cards,
  add-monitor modal, settings page for Telegram + maintenance, toasts, skeletons, empty states).
- Cleanup: remove every `RESEND_API_KEY` / email / Discord / Slack reference from config,
  `.env.example`, docs, code, and tests.

> Detailed diary follows chronologically — step-by-step actions logged below.

## Step-by-step actions performed (Phase 4)

### 4.1 — Models + migration 004
- Edited `app/core/config.py:24` — removed `resend_api_key`, added `telegram_bot_token=""` + `telegram_escalation_delay_min=10` (env-driven, 10 min per your choice). ✅
- Created `app/models/notification_channel.py` — `notification_channels` (team_id FK CASCADE, type String(20) CHECK `type='telegram'`, telegram_chat_id String(64), label, is_active, TimestampMixin). Index on (team_id, type).
- Created `app/models/maintenance_window.py` — `maintenance_windows` (team_id FK CASCADE, monitor_id nullable FK CASCADE null=whole-team, starts_at/ends_at DateTime tz, reason, created_by SET NULL). Indexes on (team_id, starts_at) + monitor_id.
- Created `app/models/alert_log.py` — `alert_logs` (UUID pk, team_id/ incident_id SET NULL/ channel_id SET NULL/ monitor_id SET NULL, kind CHECK open/recovery/escalation/test, status CHECK sent/failed/skipped, attempts, error, telegram_message_id, sent_at/created_at). Indexes on incident_id, channel_id, (team_id, sent_at).
- Edited `app/models/incident.py:47` — added `escalated_at DateTime(tz) nullable` for one-time escalation tracking.
- Updated `app/models/__init__.py` — exported 3 new models. ✅
- Ran `uv run alembic revision --autogenerate -m "004 ..."` → `208e02f76b2c_004_...py` (detected 3 tables + 1 column) → `uv run alembic upgrade head` → head `208e02f76b2c` verified. ✅

### 4.2 — Repositories + services + Telegram sender
- Created `app/repositories/notification_channel_repository.py` (list_for_team, list_active_for_team, get_by_id, create, delete).
- Created `app/repositories/maintenance_repository.py` (list_for_team, get_by_id, find_active_for_monitor with `((monitor_id IS NULL) OR (monitor_id == :mid))` null=whole-team logic, create, delete).
- Created `app/repositories/alert_log_repository.py` (create).
- Created `app/repositories/incident_repository.py` (get_by_id, list_for_team, list_for_monitor, get_open_for_monitor).
- Created `app/services/telegram_service.py` — `send_message(chat_id, text)` via `httpx.AsyncClient` 10s timeout, `POST https://api.telegram.org/bot{token}/sendMessage` with `parse_mode=Markdown`, 3 retries `BACKOFF [1,3,8]s`, handles 429 `retry_after` sleep, returns `(ok, error, message_id)` never raises. Helpers `build_open_message / build_recovery_message / build_escalation_message / build_test_message`. Injectable `_client` via `set_client_for_testing` (MockTransport).
- Created `app/services/alert_service.py` — `is_in_maintenance()` (now check), `send_for_incident()` (maintenance gate → no-channel skip → build text once → loop channels → `telegram_service.send_message` → `alert_log.create` per channel → commit, returns per-channel results), `send_test_for_channel()`, `should_escalate()` (OPEN + ack_at null + escalated_at null).
- Result: 0→ Telegram-only, no email/Discord code paths remain. ✅

### 4.3 — Worker jobs + checker integration
- Created `app/workers/alerter.py` — `telegram_alert_job(ctx, incident_id, kind)` (loads incident+monitor, dedupes escalation via `should_escalate`, calls `alert_service.send_for_incident`, on `kind==open` and any sent → `ctx["redis"].enqueue_job("telegram_alert_job", id, "escalation", _defer_by=10*60)`, on escalation success sets `incident.escalated_at=now`), `telegram_test_job`, `sweep_stale_escalations(ctx)` (cron fallback every minute: selects OPEN 10m+ unacked where started_at <= cutoff and escalated_at null, respects maintenance, enqueues escalation — makes free-tier sleep safe).
- Edited `app/workers/checker.py:104` — after `apply_flap_logic` + `commit`, remembers `incident_kind` (open/recovery) and enqueues `telegram_alert_job` via `ctx["redis"].enqueue_job`. Does not fail the check if Redis is full. Flap still idempotent.
- Edited `app/workers/settings.py:3` — added imports `telegram_alert_job, telegram_test_job, sweep_stale_escalations`, `functions=[check_job, telegram_alert_job, telegram_test_job]`, `cron_jobs=[enqueue_due_monitors every 30s, sweep_stale_escalations every 60s @ :15]`. Worker now 5 functions. ✅
- Verified `docker logs pulsetrack-ai-worker-1` → `Starting worker for 5 functions: check_job, telegram_alert_job, telegram_test_job, cron:enqueue_due_monitors, cron:sweep_stale_escalations` ✅

### 4.4 — API routers (9 new endpoints)
- Created `app/schemas/notification_channel.py` (TelegramChannelIn: chat_id 3-64 chars, label; TelegramChannelOut; TelegramTestOut).
- Created `app/schemas/maintenance.py` (MaintenanceIn: monitor_id nullable null=whole-team, starts_at/ends_at tz-aware, validator 1 min–24h, ends>starts; MaintenanceOut).
- Created `app/schemas/incident.py` (IncidentOut: id/team_id/monitor_id/status/started_at/ack_at/resolved_at/downtime_sec/escalated_at/created_at).
- Created `app/api/v1/routers/notification_channels.py` — `GET /notification-channels` (list own), `POST /notification-channels` 201 (validates chat_id numeric after stripping `-`, creates, audit `notification_channel.created`), `DELETE /notification-channels/{id}` (tenancy 404), `POST /notification-channels/{id}/test` (loads best monitor for richer text, calls `telegram_service.send_message` directly, logs alert_log, on fail raises `AppError 502 TELEGRAM_FAILED` with gateway error, on ok 200 `{ok:true}`).
- Created `app/api/v1/routers/maintenance.py` — `GET /maintenance`, `POST /maintenance` 201 (validates monitor belongs to team if set, audit), `DELETE /maintenance/{id}`.
- Created `app/api/v1/routers/incidents.py` — `GET /incidents?status`, `GET /incidents/{id}`, `POST /incidents/{id}/acknowledge` (only OPEN → ACK, sets ack_at, audit, 400 if not OPEN), `GET /incidents/by-monitor/{mid}` (tenancy via monitor lookup).
- Wired all three in `app/api/v1/__init__.py:1` — `api_router` now 6 routers. ✅

### 4.5 — Config + Docker wiring (telegram-only)
- `docker-compose.yml:43` — api + worker both get `TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}` + `TELEGRAM_ESCALATION_DELAY_MIN=${...:-10}`.
- `.env.example:15` — removed `RESEND_API_KEY`, added `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ESCALATION_DELAY_MIN=10` (with BotFather hint). `backend/.env` (gitignored, never committed) created locally with the real token for dev — proves token never appears in git. ✅

### 4.6 — Verification (backend)
- `uv run ruff check app` → All checks passed after wrapping 12 E501 long lines + fixing I001 imports via `ruff --fix`. ✅
- `uv run pytest -q` → **47 passed** (all Phase 1-3 tests still green; no regression from new tables — new endpoints are extra, old behavior untouched). ✅
- `docker compose up -d --build` (both api+worker images rebuilt, 3.0s) → api+worker Up, `/health`→`ok`, worker log shows 5 functions. ✅
- Live smoke vs Docker (real Postgres+Redis):
  - register s4-* → 201
  - GET /notification-channels → `[]`
  - POST channel `123456789` → 201
  - GET channels → 1 row
  - POST /notification-channels/{id}/test with fake chat → `502 TELEGRAM_FAILED` (correct: gateway error propagated as structured `{error:{code}}`)
  - POST /monitors → 201
  - POST /maintenance whole-team + per-monitor → 201/201, GET list → 2 rows
  - GET /incidents → 0
  - DELETE channel → 200 (all tenancy + audit paths work). ✅
- Telegram Bot check: `GET /bot<token>/getMe` → `ok:true username:PulseTrackAlertBot` (token valid). `getUpdates` → `[]` (awaiting user /start in Private DM — see "Needs from you" below). ✅

### 4.7 — Frontend UI/UX premiumized light (kept light, made production-grade)
- New `frontend/src/components/Toast.tsx` — `ToastProvider` + `useToast()` hook (bottom-right, 3s auto-dismiss, ok/err tones). Wrapped in `App.tsx:14`.
- Edited `frontend/src/types.ts:26` — added `TelegramChannel, MaintenanceWindow, IncidentOut`.
- Edited `frontend/src/App.tsx:1` — added `/settings` protected route, `ToastProvider`, background `#f8fafc`.
- Rewrote `frontend/src/pages/Dashboard.tsx` (257→ ~280 lines):
  - Sticky blurred header `bg-white/80 backdrop-blur` with mini `P` badge, team pill, Settings + Log out buttons.
  - Overview header + light copy "Telegram tells you when they go down".
  - Stat cards `StatCard` with `border-slate-200`, top `h-1` indigo→violet gradient, `rounded-2xl`, shadow-sm, conditional red ring on down>0.
  - Monitors toolbar `MONITORS` label + indigo `+ Add monitor` (shadow-indigo).
  - Table `rounded-2xl border shadow-sm`, header `bg-slate-900`, status pills `rounded-full ring-1` with `STATUS` map (emerald dot with glow, red dot animate-pulse for DOWN), latency color `latencyColor()` (<220 emerald, <600 amber, else red), interval chip `bg-slate-100`, time as `relativeTime()` (just now/2m ago/1h ago), hover `bg-indigo-50/40`, actions as bordered buttons Pause/Resume + owner Delete with confirm.
  - Empty state centered icon `◯` + copy "checks are UP again" + CTA, loading skeletons `animate-pulse`.
  - Auto-refresh footer links to Settings.
  - Add-monitor now a **modal** (fixed overlay `bg-slate-900/40 backdrop-blur-sm`, `rounded-2xl border shadow-xl`, fields with `rounded-xl` + `focus:ring-4` indigo, validation, toast on success, free-plan note).
- Created `frontend/src/pages/Settings.tsx` — header `← Back to Dashboard` + Telegram + Maintenance sections:
  - Telegram: Chat ID + label inputs + Add, list channels with Test (indigo) + Remove (red), empty dashed box hint, helper `curl .../getUpdates`.
  - Maintenance: monitor selector (All or name) + reason + starts/ends `datetime-local` + Create, list windows with Cancel.
  - All wired via TanStack Query (`channels`, `maintenance`, `monitors` queries, mutations with `invalidateQueries` + `useToast` + `errorMessage`).
- Verified `npm run build` → `tsc -b + vite build` green `146 modules`, `384.17 kB` bundle. `npm run lint` → 1 warning only (`react/only-export-components` for useToast — harmless, lint exit 0). ✅

### 4.8 — Docs + cleanup
- `README.md:1` — "email / Discord / Telegram" → "Telegram Bot" only; updated Run locally (Phase 4) with BotFather + `TELEGRAM_BOT_TOKEN` step + frontend `npm run dev`; replaced endpoint table from 10 → ~21 endpoints including 9 new Phase 4 routes; added Telegram alert lifecycle note (OPEN/recovery/10m escalation, muted in maintenance, 3× retry, alert_logs).
- Grep for user-login email stays (auth uses email) — correct. Alert channel references now exclusively Telegram; no `RESEND`/`Discord`/`Slack` in `app/` except auth emails. ✅

### 4.9 — Decisions made in Phase 4
1. Single global Bot token + per-team chat_id (vs per-team bot) — one secret to manage, matches free-tier simplicity, team isolation via row ownership.
2. `type CHECK type='telegram'` at DB level — future multi-channel would need migration, but current rule "telegram only" is enforced at storage not just code.
3. Maintenance null=whole-team semantic — handled with `OR (monitor_id IS NULL)` predicate, avoids N windows per deploy.
4. Alerts run as ARQ jobs, not inline in request or check probe — keeps API <50ms and check probe <10s even when Telegram is slow. Retry inside `telegram_service`, not ARQ max_tries.
5. Escalation dual-path: fast path via `_defer_by` 10 min + cron fallback `sweep_stale_escalations` every minute for sleep/reconnect safety (free tier worker may sleep).
6. `alert_logs` always written — even `skipped:maintenance` / `skipped:no_channel` — so the audit trail answers "why didn't I get a message?"
7. `POST .../test` calls Telegram directly (not enqueued) so user gets instant success/fail feedback in the UI; logs the attempt same as real alerts.
8. Frontend kept light (`#f8fafc`, white cards, indigo primary) per your choice — premium via spacing, rounded-2xl, gradients, pill statuses, backdrop blur, not a dark theme switch.
9. Toast via context provider, not a third-party lib — zero-bundle-cost.

### 4.10 — Current state (end of Phase 4 diary batch)
- Stack: api :8000, worker (5 functions + 2 crons), db :5433, redis :6379 — all Up, health ok.
- DB head `208e02f76b2c` — tables: teams, users, audit_logs, monitors, checks, incidents(+escalated_at), notification_channels, alert_logs, maintenance_windows.
- Endpoints: ~21 live (9 Phase 1 + 9 Phase 2 + 3 new channel/maintenance/incident ACK groups).
- Frontend: Dashboard premium light + /settings (Telegram + Maintenance) + toasts/modals; build green.
- Tests: 47 green, ruff clean, Docker rebuilt.
- Secret: real `TELEGRAM_BOT_TOKEN` in `backend/.env` (gitignored) + compose `${VAR:-}` — never committed.

### 4.11 — Telegram auto-connect Option A (polling) + Northflank Sandbox deploy target
- Goal: kill manual chat-ID copy-paste. Flow: Settings [Connect Telegram] → open bot → press Start → backend auto-creates channel → ✅. 100% free (Telegram Bot API + getUpdates polling, no webhook/public URL needed).
- Backend:
  - `app/core/config.py` — added `telegram_bot_username=""` (for `t.me/Bot?start=TOKEN`) + `telegram_link_expire_min=15`.
  - `app/services/telegram_service.py` — added `get_bot_username()`, `build_deep_link()`, `parse_start_payload()` (`/start <token>` extractor), `get_updates()` (never-raises `getUpdates` wrapper), `build_connected_message()`.
  - Created `app/services/telegram_link_service.py` — Redis one-time tokens: `tg_link:{token}` (JSON team_id/user_id/label, TTL 15 min), `tg_link_done:{token}` (channel_id, TTL 10 min for UI status), `tg_update_offset` (getUpdates offset). Helpers `create_link/get_link/consume_link/mark_connected/cancel_link/get_offset/set_offset`, redis-injected for tests.
  - `app/schemas/notification_channel.py` — added `TelegramConnectIn/Out` (`token, deep_link, expires_in_sec`) + `TelegramConnectStatusOut` (`pending|connected|expired` + channel).
  - `app/repositories/notification_channel_repository.py` — added `find_by_chat_id(team, chat_id)` for idempotent auto-create (same DM pressed twice ≠ duplicate rows).
  - `app/api/v1/routers/notification_channels.py` — added `POST /notification-channels/connect` (Member+, creates token + deep link), `GET /connect/{token}/status` (team-scoped pending/connected/expired), `DELETE /connect/{token}` (cancel). Manual `POST /` kept as Advanced fallback for groups/supergroups (deep-link Start is DM-only).
  - Created `app/workers/telegram_poller.py` — `poll_telegram_updates(ctx)` cron body: skip when no token, `getUpdates(offset)`, parse `/start <token>`, `consume_link`, dedupe by chat_id, create channel + `audit notification_channel.created via=telegram_auto_connect`, best-effort ✅ welcome message, `mark_connected`, advance offset always. Never raises.
  - `app/workers/settings.py` — `functions=[..., poll_telegram_updates]`, `cron poll_telegram_updates second={10,40}` (offset from checks at :00/:30). Worker now 6 functions + 3 crons.
  - `.env.example` + `docker-compose.yml` (api+worker) — added `TELEGRAM_BOT_USERNAME`, `TELEGRAM_LINK_EXPIRE_MIN`.
- Frontend:
  - `src/types.ts` — added `TelegramConnect`, `TelegramConnectStatus`.
  - Rewrote `src/pages/Settings.tsx` Telegram section: 1-2-3 step cards, live connected pill, `[ⓣ Connect Telegram]` + optional label, auto-`window.open(deep_link)`, waiting card with spinner + `m:ss` countdown + status poll every 3s (`GET /connect/{token}/status`), Open-again / Copy-link / Cancel buttons, success banner `connected ✅`, channel list with green dot + Test/Remove, manual group form moved into `<details> Advanced`.
- Deploy target change (per user): backend api + ARQ worker → **Northflank Sandbox** (2 always-on services free, no 15-min sleep like Render free; Render has no free Background Worker). Frontend → Vercel, Postgres → Neon (permanent free), Redis → Upstash (persistent free). Updated `README.md` stack + run-locally + API table + Telegram + deploy notes, `docker-compose.yml` comments (Render → Northflank), `app/main.py /health` docstring.
- Verification: `ruff check` + `pytest -q` + `npm run build` (see 4.12).

### 4.12 — Current state (after auto-connect)
- Stack: api :8000, worker (6 functions + 3 crons), db :5433, redis :6379.
- Endpoints: ~24 live (+3 connect endpoints).
- Frontend: Settings auto-connect UX + Maintenance untouched; build green.
- Secrets: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME` in `backend/.env` (gitignored).

## Next: Phase 5 — Live WS + Public Page + Heartbeat
Redis pub/sub → WS `/ws/monitors`, public `/status/{slug}` cached 30s, heartbeat ping.

---

# PHASE 5 — Live WS + Public Status Page + Heartbeat (IN PROGRESS — started 2026-09-17)

**Goal (roadmap Phase 5):** make the dashboard feel alive (no refresh), give each team a
shareable public status link (no login, works in incognito), and add reverse monitors
(heartbeats) for cron jobs — all $0, all on Northflank Sandbox + Vercel + Neon + Upstash.

> Diary follows chronologically — one entry per action. No code written yet (kickoff only).

### 5.0 — Kickoff + plan locked (2026-09-17)
- Read current state: api (FastAPI, no WS yet), worker (`check_job` saves checks, no publish yet),
  Redis (queue + locks + link tokens, no pub/sub yet), teams have `slug` (ready for `/s/{slug}`),
  no `heartbeats` table/model/migration yet, `uvicorn[standard]` already includes WebSocket support.
- Locked scope for Phase 5 (3 features, nothing more):
  - A. Live updates: worker publishes each check result to Redis pub/sub → API WS `/ws/monitors`
    (JWT via `?token=`) forwards only your team's events → Dashboard updates dots instantly.
  - B. Public status page: `GET /status/{slug}` + `/incidents` + `/badge.svg` (public, Redis-cached
    30s/60s, invalidated on new check/incident) + frontend public route `/s/:slug`.
  - C. Heartbeats: new `heartbeats` table (migration 005) + `POST/GET/DELETE /heartbeats` (JWT) +
    public `POST /heartbeats/{key}/ping` (key auth) + worker `heartbeat_checker` cron every minute
    (missing ping → Telegram alert via existing channels).
- Decisions pending user confirmation (see chat 2026-09-17): public page hides full URLs (names +
  status only); no email subscribe in Phase 5 (Telegram-only); heartbeat alerts reuse existing
  Telegram channels with a simple sent/failed log (no full incident row in v1).
- Next actions in order: 5.1 Redis pub/sub + WS endpoint + worker publish → 5.2 public status API +
  cache → 5.3 heartbeat model/migration/endpoints/cron → 5.4 frontend (live dots + `/s/:slug` +
  heartbeat UI) → 5.5 tests + docs + roadmap regen.
- User confirmed `yes to all` (2026-09-17) → build started in that order.

### 5.1 — Live updates: worker publish + WS /ws/monitors (DONE 2026-09-17)
- Created `app/services/live_service.py` — `LIVE_CHANNEL="live"`, `build_check_event()` (team/monitor/status/latency/code/checked_at/incident), `publish_check()` (best-effort, never raises), `public_*_key()` builders + `invalidate_public_cache()` (best-effort delete of 3 keys).
- Edited `app/workers/checker.py` — after commit, publishes check event via `redis_client` (AFTER commit so subscribers never see rolled-back rows); on incident or DOWN also invalidates that team's public cache via slug lookup. Alert enqueue untouched. Publish failures swallowed (live never fails a probe).
- Created `app/api/ws.py` — `WS /ws/monitors?token=<JWT>`: validates access token once (type/blacklist/user-active, 4401 close on fail), sends `{"type":"hello"}`, subscribes to `live`, forwards only same-`team_id` messages, answers client `ping` with `pong`, cleans up pubsub on disconnect. No new dependency (`uvicorn[standard]` already has WS).
- Edited `app/main.py` — `app.include_router(ws_router)` (WS has no OpenAPI entry, verified via router import + auth unit test instead).
- Verified: `ruff` clean (fixed 2 UP041 `asyncio.TimeoutError` → `TimeoutError` via `--fix`), `pytest -q` 47 passed, `_auth_ws` unit check (valid → user, missing/garbage → rejected, route `/ws/monitors` registered).

### 5.2 — Public status API + cache + badge (DONE 2026-09-17)
- Created `app/schemas/status.py` — `PublicMonitorOut` (id/name/status/latency/checked_at, NO url), `PublicStatusOut` (team_name/slug/overall/open_incidents/monitors), `PublicIncidentOut` (monitor_name + times, NO emails/chat IDs).
- Created `app/api/v1/routers/status.py` (public, no auth) — `GET /status/{slug}` (overall = outage if all unpaused DOWN else degraded if any DOWN/open else operational; cached 30s `public:{slug}`), `GET /status/{slug}/incidents` (`?limit` 1–100, cached 30s), `GET /status/{slug}/badge.svg` (green/red SVG, cached 60s). All payloads validated before caching; Redis failures fall through to DB (cache never breaks the page); unknown slug → 404.
- Mounted twice: under `/api/v1` (`api_router`, works with Vite dev proxy + `VITE_API_URL`) AND at root (`main.py`, roadmap-canonical `/status/{slug}`). Badge snippet uses root URL.
- Verified E2E (ASGI, test DB): slug lookup, monitor create → both URLs 200, monitors contain NO url string, incidents `[]`, badge `image/svg+xml`, unknown slug 404, 2nd status call served from cache 200.

### 5.3 — Heartbeats: model + migration 005 + endpoints + cron (DONE 2026-09-17)
- Created `app/models/heartbeat.py` — `heartbeats` (team FK CASCADE, name, `ping_key` unique+indexed secret, period 1–10080 min, grace 0–1440 min, `last_ping_at`, status ALIVE/MISSING + CHECKs, index on team_id). Exported in `models/__init__.py`.
- Created `app/repositories/heartbeat_repository.py` (list/get-by-id/get-by-key/create/delete), `app/schemas/heartbeat.py` (`HeartbeatIn`, `HeartbeatOut`, `HeartbeatCreatedOut` with one-time `ping_key`).
- Added `build_heartbeat_down_message` (💔 silent N min) + `build_heartbeat_recovery_message` (💚) to `telegram_service.py`.
- Created `app/api/v1/routers/heartbeats.py` — `POST /heartbeats` (Member+, `hb_<urlsafe>` key, audit `heartbeat.created`, key returned ONCE), `GET /heartbeats`, `DELETE /heartbeats/{id}`, `POST /heartbeats/{key}/ping` (public key-auth; sets ALIVE + on MISSING→ALIVE sends recovery to team channels, `alert_logs` kind=recovery + cache invalidate). Unknown key → 404.
- Created `app/workers/heartbeat_checker.py` — cron body every minute: ALIVE rows silent past period+grace (or never-pinged since creation) → MISSING + 💔 Telegram via existing channels (`alert_logs` kind=open, monitor/incident None — fits CHECK; `skipped/no_channel` when no channels). Commits once. Idempotent (2nd run sends nothing).
- `app/workers/settings.py` — added `heartbeat_checker` to functions + `cron(..., second={20})`. Worker now 5 job functions + 4 crons. Migration `3241a637104e_005_heartbeats` autogenerated (added table + 2 indexes) + `alembic upgrade head` applied locally. Restarted Docker worker → log `Starting worker for 9 functions: ... heartbeat_checker ... cron:heartbeat_checker` ✅.
- Verified E2E: create (key once) → ping ALIVE → list → bad key 404 → delete → ping 404; checker (30-min-silent row) → `checked=1 missing=1`, 1 Telegram sent, status MISSING, 1 `alert_logs(open)`, 2nd run `checked=0` no resend.

### 5.4 — Frontend: live dots + /s/:slug + heartbeat UI (DONE 2026-09-17)
- `src/types.ts` — added `TeamDetail, LiveCheckEvent, PublicMonitor/Status/Incident, Heartbeat, HeartbeatCreated`.
- Created `src/hooks/useLiveMonitors.ts` — WS to `:8000/ws/monitors?token=` in dev (`VITE_API_URL` backend base in prod), patches `["monitors"]` cache per check event (paused rows untouched), exponential reconnect backoff (max 15s), 25s `ping` keep-alive, returns `live` boolean. 30s `refetchInterval` polling kept as fallback.
- `src/pages/Dashboard.tsx` — `LIVE`/`SYNCING` pill in Overview header (title explains fallback) + `View public status page →` link (from `/teams/me` slug).
- Created `src/pages/StatusPage.tsx` — public route (no auth): big overall banner (green/amber/red), monitors list with dots, recent incidents, README badge snippet (backend-base URL). 30s refetch. 404 state for bad slug.
- `src/App.tsx` — added public route `/s/:slug`.
- `src/pages/Settings.tsx` — new Heartbeats section: explain + one-time ping-URL box (Copy / I-saved-it), create form (name/every/grace), list with ALIVE/MISSING dots + last-ping + Delete (confirm).
- Verified: `npm run build` green (148 modules; fixed 1 unused `unwrap` import), `npm run lint` 0 errors (3 pre-existing-style warnings).

### 5.5 — Verification + docs (DONE 2026-09-17)
- `uv run ruff check app` → clean. `uv run pytest -q` → 47 passed (no regressions; new endpoints covered by manual E2E scripts, formal tests land in Phase 8).
- `README.md` — header → Phase 5 state; frontend line → LIVE + `/s/{slug}` + heartbeats; API table → +9 rows (WS, 3 status, 4 heartbeat); added live/heartbeat paragraph.
- Roadmap PDF (`generate_roadmap_pdf.py` / `PulseTrack-AI-Roadmap.pdf`): plan text already described Phase 5 exactly as built — no regen needed.

### 5.7 — Heartbeat ping box: full PowerShell command + env-aware URL (per user, 2026-09-17)
- Problem (user screenshot): revealed ping box showed a relative path `/api/v1/heartbeats/hb_.../ping` — not paste-ready, and would break after deploy (localhost → Northflank).
- Edited `frontend/src/pages/Settings.tsx` — added `backendBase()` (`VITE_API_URL` base in prod, `:8000` in Vite dev, origin otherwise); `pingUrl()` now absolute; new `pingCommand()` returns `curl.exe -X POST "<url>"`. Box now says "Paste this in PowerShell", code shows the full command, Copy copies the command, note explains the URL follows the environment (localhost now, Northflank URL after deploy, zero edits).
- Roadmap files: plan doc only references generic `POST /heartbeats/{key}/ping` (no hardcoded host) — still accurate, no regen needed.
- Verified: `npm run build` green (148 modules), `lint` 0 errors.
- Live stack restarted: Docker worker on new code (9 functions incl. `heartbeat_checker` cron ✅); api hot-reloads via volume mount.
- Manual smoke checklist for user (needs browser): Dashboard shows LIVE → kill a monitor URL → dot flips without refresh; incognito `/s/{slug}` works; create heartbeat → `curl -X POST <pingUrl>` → ALIVE; wait past period+grace → 💔 Telegram.

### 5.6 — Removed README badge (per user, 2026-09-17)
- User: badge not useful → removed `GET /status/{slug}/badge.svg` entirely (was green/red SVG, 60s cache).
- Edited `app/api/v1/routers/status.py` — deleted badge endpoint + `Response` import, docstring updated (2 endpoints left).
- Edited `app/services/live_service.py` — deleted `public_badge_key()`; `invalidate_public_cache()` now deletes 2 keys (`public:{slug}`, `public:{slug}:incidents`).
- Edited `frontend/src/pages/StatusPage.tsx` — deleted badge-snippet section + `backendBase()` helper.
- Edited `README.md` — deleted badge row from API table.
- Roadmap plan doc (`generate_roadmap_pdf.py`/PDF) untouched — it records the original plan; this diary records the deviation.
- Verified: `ruff` clean, `pytest` 47 passed, `npm run build` green.

---

# PHASE 6 — Gemini AI Incident Analyst (IN PROGRESS — started 2026-09-17)

**Goal (roadmap Phase 6):** one-click AI root-cause explanation per incident + copy-paste
customer status draft + ask-about-my-outages — all on Gemini 2.0 Flash free tier, cached so
hardly any paid/quota calls ever happen. AI never runs in the check loop (only on click).

> Diary follows chronologically — one entry per action. No code written yet (kickoff only).

### 6.0 — Kickoff + plan locked (2026-09-17)
- Read current state: `gemini_api_key=""` in config + `.env.example` (no real key yet),
  `incidents.ai_summary` column exists (empty for all rows), no AI service/router/schema yet,
  `httpx` available for the Gemini REST call, Redis available for 24h cache, incident detail
  currently API-only (`GET /incidents/{id}`) — no frontend incidents UI (Dashboard has monitors
  table only), so the Explain button needs a new home.
- Locked scope for Phase 6 (4 endpoints + UI, nothing more):
  - `POST /incidents/{id}/analyze` (Member+) — cache-first, else 1 Gemini call, save to
    `incidents.ai_summary` + Redis 24h. Rate-limit 10/min/user. 20s timeout. 429 → graceful
    "AI busy" fallback, never crashes.
  - `GET /incidents/{id}/analysis` (Bearer) — cached read only (~50ms, $0, zero Gemini calls).
  - `POST /incidents/{id}/draft-update {tone}` (Member+) — 2-sentence customer message,
    copy-paste ready. Same cache/quota rules.
  - `POST /ai/ask {question}` (Member+) — keyword search over own team's past incidents +
    1 Gemini call to answer ("why down Tuesday?").
  - Frontend: new Incidents page (`/incidents`): OPEN/RESOLVED list + timeline + Explain button
    + Draft box + Acknowledge button (also closes the earlier "how to ack" gap — one UI, two uses).
- Quota math locked: prompt = last 20 checks only (~800 tokens), temperature 0.2, max 400 tokens
  output, log tokens per call. 50 demo clicks ≈ <10 real Gemini calls thanks to cache.
- Needs from user (see chat 2026-09-17): real `GEMINI_API_KEY` + UI placement confirmation.
- User supplied key + `start` (2026-09-17). Key stored in `backend/.env` + root `.env`
  (both gitignored, never committed). Verified live before building.
- Next actions in order: 6.1 AI service (prompt builder + REST caller + cache) → 6.2 endpoints +
  rate-limit → 6.3 Incidents page (explain + draft + ack) → 6.4 tests + docs.

### 6.1 — Key verify + model discovery (DONE 2026-09-17)
- Saved user key to both `.env` files. Test call: key VALID, but `gemini-2.0-flash` returns
  404 "no longer available". Listed models: `2.5-flash`/`2.5-flash-lite` also 404 for new users.
  Verified working: `gemini-3.5-flash-lite` → 200 `OK` (6 tokens) and `gemini-3.6-flash` → 200.
  Locked model = `gemini-3.5-flash-lite` (cheapest/fastest free-tier text model).
- `app/core/config.py` — added `gemini_model="gemini-3.5-flash-lite"` (env-overridable).
  `.env.example` + `docker-compose.yml` (api+worker) — added `GEMINI_API_KEY`/`GEMINI_MODEL`.
- Created `app/services/ai_service.py` — pure builders `build_analyze_prompt` (last 20 checks,
  150-word SRE format), `build_draft_prompt` (tone), `build_ask_prompt` (top-5 history grounded);
  `call_gemini()` (20s timeout, temp 0.2, max 400 tokens, never raises: missing-key/429/other
  mapped to error strings, token usage logged); `cache_get/cache_set` (Redis-injected);
  `analyze_for_incident()` (Redis → DB → 1 call → save both) + `draft_for_incident()` (per-tone key).
  Injectable `_client` via `set_client_for_testing` (MockTransport, same pattern as telegram).
- Created `app/core/rate_limit.py` — fixed-window `check_rate_limit()` (INCR+EXPIRE, 429 AppError
  with Retry-After; fails open on Redis blip).

### 6.2 — Endpoints: analyze/analysis/draft/ask (DONE 2026-09-17)
- `app/schemas/ai.py` — `AnalysisOut/DraftIn(tone literal)/DraftOut/AskIn/AskOut`.
- `app/api/v1/routers/incidents.py` — added `POST /{id}/analyze` (10/min, cache-first, summary→200
  else 503 AI_NOT_CONFIGURED / 502 AI_FAILED), `GET /{id}/analysis` (cached-only, uncached→404
  AI_NO_ANALYSIS, NOT rate-limited — costs $0), `POST /{id}/draft-update` (10/min, per-tone cache).
  Tenancy via shared `_owned_incident/_owned_monitor` (cross-team → 404).
- Created `app/api/v1/routers/ai.py` — `POST /ai/ask` (10/min): team's incidents (limit 100) +
  monitor names, keyword-overlap ranking (name×implicit, top-5), 1 grounded Gemini call; empty
  history answers without any call ($0). Wired in `api/v1/__init__.py`.
- Verified E2E vs test DB with REAL Gemini: analyze 200 fresh (correct 500 diagnosis) → 2nd call
  cached → GET cached → draft friendly OK → ask grounded OK → cross-team 404 → 11th+ call 429.

### 6.3 — Frontend Incidents page (DONE 2026-09-17)
- `src/types.ts` — added `Analysis, Draft, AskAnswer`.
- Created `src/pages/Incidents.tsx` (`/incidents`, protected): status filter ALL/OPEN/ACK/RESOLVED,
  list + detail, ✨ Explain (shows cached-$0 note), tone select + Draft + Copy, Acknowledge button
  on OPEN (also closes the earlier "how to ack" gap — no more curl needed), Ask box at the bottom.
- `src/App.tsx` — added `/incidents` route. `Dashboard.tsx` header — added ✨ Incidents link.
- Verified: `npm run build` green (149 modules), `lint` 0 errors (2 pre-existing warnings).

### 6.4 — Verification + docs (DONE 2026-09-17)
- Created `backend/tests/test_ai.py` — 15 tests: prompt truncation (20/30 checks), 429→quota,
  no-key no-network, cache-hit with failing transport (0 calls), 404-before-analyze, 502 fallback,
  cross-team 404, invalid tone 422, 11th-call 429, ask with/without history, limiter unit test.
- `uv run ruff check app tests` → clean. `uv run pytest -q` → **62 passed** (47 old + 15 new).
- `docker compose up -d` (recreate api+worker with GEMINI env) → verified inside api:
  key set, model `gemini-3.5-flash-lite`. Live-stack check via demo login: OPEN dummy incident →
  analyze 200 fresh, diagnosis correct ("DNS resolution failure / nonexistent domain").
- `README.md` — Phase 6 header, Incidents frontend line, +4 API rows, AI paragraph (key link,
  model note, cache/rate-limit rules), tests → 62.

### 6.5 — Removed customer draft + Ask answers like a general AI (per user, 2026-09-17)
- User: (1) draft box not useful → remove; (2) Ask refused "give me a solution" with
  "history has no answer" — should answer accurately like a general AI.
- Root cause of (2): `build_ask_prompt` instructed "only from the history above, else refuse".
  Fix: history is now *primary context* (cited when relevant) + general SRE knowledge allowed,
  labeled briefly, with "Never refuse". Verified live vs real Gemini: "give me a solution" →
  200 with 4 actionable steps (ack/assign, telemetry, impact, resolve) instead of refusal.
- Removed full-stack: `POST /incidents/{id}/draft-update` route, `DraftIn/DraftOut`,
  `build_draft_prompt`/`draft_for_incident`/`draft_key`, frontend Draft box + tone state,
  `Draft` TS type, README row + frontend line, 2 draft tests (replaced with
  never-refuse/general-knowledge prompt test).
- Verified: `ruff` clean, `pytest` **61 passed**, `npm run build` green, `lint` 0 errors.

---

# PHASE 7 — API Keys + Outbound Webhooks + Audit Trail (IN PROGRESS — started 2026-09-18)

**Goal (roadmap Phase 7):** turn PulseTrack into a platform others can automate — machine keys
for scripts/CI, signed incident webhooks for user URLs, and a readable audit trail. No new paid
service, no new env vars.

> Diary follows chronologically — one entry per action. No code written yet (kickoff only).

### 7.0 — Kickoff + plan locked (2026-09-18)
- Read current state: no `api_keys` / `outbound_webhooks` tables, models, or routers yet;
  all auth is JWT-only (`get_current_user`, role deps owner/member/viewer); `audit_logs` table +
  `audit_repository.log()` exist and every write path already logs (monitors, teams, channels,
  heartbeats, incident ack) with `user_id` nullable + JSON `detail`; no `GET /audit-logs` reader yet;
  worker has `checker` (knows OPEN/RECOVERY transitions) + ARQ queue for new delivery jobs.
- Locked scope for Phase 7 (4 builds, nothing more):
  - 7.1 API keys: `api_keys` table (migration 006) + `POST/GET/DELETE /api-keys` (Owner creates,
    key shown ONCE as `pk_live_...`, SHA256 hash stored, prefix for lookup, revoke = delete) +
    Bearer `pk_` accepted everywhere JWT is (key → creator user, same roles/audit).
  - 7.2 Outbound webhooks: `outbound_webhooks` table (migration 007) + CRUD + Test button +
    `webhook_delivery_job` (ARQ, 3× retry) firing signed JSON on incident OPEN/RECOVERY with
    HMAC-SHA256 `X-Signature` + timestamp; deliveries logged to `audit_logs`.
  - 7.3 Audit reader: `GET /audit-logs` (Owner, `?user&action&page&limit`).
  - 7.4 Frontend Settings: Keys section (create → show-once modal, prefix list, revoke) +
    Webhooks section (URL + auto secret, Test, delete) + Audit section (who did what).
  - 7.5 Tests (hash-only storage, revoked/unknown key 401, cross-team 404, HMAC verify,
    bad-secret test fails cleanly) + README curl docs + diary.
- Decisions pending user confirmation (see chat 2026-09-18): key inherits creator's role;
  webhook events = incident open/recovery only; secret auto-generated when blank.
- Next actions in order: 7.1 keys → 7.2 webhooks → 7.3 audit reader → 7.4 frontend → 7.5 tests+docs.
- User confirmed `yes to all` (3 decisions) → build started in that order.

### 7.1 — API keys backend (DONE 2026-09-18)
- Created `app/models/api_key.py` — `api_keys` (team FK CASCADE, user FK CASCADE so keys die
  with deactivation, name, prefix unique+indexed, key_hash SHA256 unique). Exported in models.
- Created `app/repositories/api_key_repository.py` — `generate_raw_key()` (`pk_live_`+urlsafe32),
  `hash_key/verify_key` (SHA256 + constant-time compare), `prefix_of` (12 chars), `create`
  (prefix pre-checked, unique constraint as race backstop), list/get/delete.
- Edited `app/api/deps.py` — dual-auth `get_current_user`: `pk_` prefix → prefix lookup +
  hash verify → creator user (active + same team, else 401), stamped `api_key_prefix`;
  else existing JWT path untouched. `TokenPayloadDep` (refresh/logout) stays JWT-only.
- Created `app/schemas/api_key.py` (`ApiKeyIn/Out/CreatedOut` with show-once `key`) +
  `app/api/v1/routers/api_keys.py` (Owner-only POST mint/GET list/DELETE revoke + audit).
  Wired in `api/v1/__init__.py`. Migration `f8e6f39ad2a1_006_api_keys` applied.
- Verified E2E (test DB): mint (raw once, prefix match, hash-only in DB) → key auths as creator →
  key creates monitor → bad key 401 → revoke → instant 401.

### 7.2 — Outbound webhooks backend (DONE 2026-09-18)
- Created `app/models/outbound_webhook.py` — `outbound_webhooks` (team FK CASCADE, url Text,
  secret plain-by-necessity for signing, is_active). Exported in models.
- Created `app/services/webhook_service.py` — `sign_payload/verify_signature` (HMAC-SHA256 over
  `<ts>.<body>`, 5-min replay skew), `build_event` (incident.opened/resolved + team/monitor/
  incident payload), `deliver()` (10s timeout, 3× retry 30s/2m/10m, never raises, MockTransport
  injection like telegram/ai services).
- Created `app/repositories/webhook_repository.py` + `app/schemas/webhook.py`
  (`WebhookIn` with optional secret, `WebhookOut` (NO secret), `WebhookCreatedOut` (secret once
  when auto-made as `whsec_…`, `••••••••` when user-supplied), `WebhookTestOut`).
- Created `app/api/v1/routers/webhooks.py` — Member+ create (http(s) validated)/test (live sample
  delivery + `webhook.tested` audit)/delete, Bearer list; cross-team 404 everywhere.
- Created `app/workers/webhooker.py` — `webhook_delivery_job(incident_id, open|recovery)`:
  loads incident+monitor+team, per active URL signed POST, one `webhook.delivered/failed` audit
  row per URL as receipt, never raises. Hooked in `checker.py` next to the Telegram enqueue +
  registered in `WorkerSettings` (worker now 6 job functions + 4 crons).
  Migration `b035e87fd1ef_007_outbound_webhooks` applied.
- Verified E2E (mock transport): bad URL 422 → create (whsec_ once) → list leaks no secret →
  test delivers signed `incident.opened` → HMAC verifies, tampered/stale rejected → cross-team
  404 → delete OK.

### 7.3 — Audit reader (DONE 2026-09-18)
- Created `app/schemas/audit.py` (`AuditLogOut`, `AuditPage` with total/page/limit) +
  `app/api/v1/routers/audit.py` — `GET /audit-logs` Owner-only, `?action=&user=&page=&limit=`
  (limit ≤200), team-scoped, newest first. Rows stay INSERT-only (no update/delete by design).
- `pytest -q` still 61 green after 7.1–7.3 (no regressions).

### 7.4 — Frontend Settings: Keys + Webhooks + Audit (DONE 2026-09-18)
- `src/types.ts` — added `ApiKey/ApiKeyCreated/OutboundWebhook/AuditLog/AuditPage`.
- `src/pages/Settings.tsx` — API keys section (name + Create → show-once modal with Copy/I-saved-it,
  prefix list + Revoke confirm); Webhooks section (URL + optional secret, auto-secret reveal box,
  per-row Test with inline Delivered/Failed result + Remove, webhook.site tip); Audit section
  (Owner, action filter + pagination, newest-first rows). All wired via TanStack Query + toasts.
- Verified: `npm run build` green (149 modules), `lint` 0 errors (2 pre-existing warnings).

### 7.5 — Verification + docs (DONE 2026-09-18)
- Created `backend/tests/test_platform.py` — 11 tests: key mint hash-only, key auth + monitor
  create, owner-key delete (inheritance), member mint 403, unknown/revoked 401, HMAC roundtrip +
  wrong/tampered/stale rejection, webhook CRUD + signed test delivery, delivery job → audit receipt,
  audit owner-list/member-403/action-filter. (One red→green: member-key delete test was impossible
  by design — only owners mint — replaced with owner-inheritance + member-mint-403 tests.)
- `uv run ruff check app tests` → clean. `uv run pytest -q` → **72 passed** (61 + 11).
- Docker worker restarted → `Starting worker for 10 functions: ... webhook_delivery_job ...` ✅.
  Live-stack smoke (demo login): mint `pk_live_eLMW` → key auth 200 → audit total 16, filtered 1 →
  revoke → instant 401.
- `README.md` — Phase 7 header, +10 API rows, key/webhook explainer + machine curl block +
  receiver-side HMAC verify snippet.

### 7.6 — Team section in Settings: invite + remove with show-once login (per user, 2026-09-18)
- User: "how do people join my dashboard?" → agreed picture first (no code): Team section at top
  of Settings, invite form (email + member/viewer), show-once login modal, member list with Remove,
  owner-only controls, audit rows. Then `build it`.
- Backend (invite existed, remove did not): added `DELETE /teams/members/{member_id}` (Owner;
  400 CANNOT_REMOVE_SELF, cross-team/unknown 404, `team.member_removed` audit, login dies instantly
  via row delete, team data untouched). Self-removal block makes last-owner lockout impossible
  (owners only exist from registration; invites are member/viewer only).
- Frontend `src/pages/Settings.tsx`: Team section first (name • plan • member count, "You are owner"
  pill), invite form + role select, members list with you-badge and owner-only Remove confirms,
  show-once login modal (email / temp password + Copy login + Done). Members/viewers see the list
  read-only. `src/types.ts`: added `InviteOut`.
- Tests: 4 new in `tests/test_teams.py` (remove → list shrinks + token 401, self-remove 400,
  unknown 404, member remove 403). `ruff` clean, full suite green, frontend build green.
- `README.md`: teams table +invite/remove rows, Settings section list updated.

---

# PHASE 8 — Testing + Polish + CSV Export (IN PROGRESS — started 2026-09-18)

**Goal (roadmap Phase 8):** prove quality — CSV downloads for bosses/Excel, measured test
coverage, and a polish pass (seed data, empty states, mobile). No new product features.

> Diary follows chronologically — one entry per action. No code written yet (kickoff only).

### 8.0 — Kickoff + plan locked (2026-09-18)
- Read current state: **76 tests green** (roadmap asked 40+ — already doubled), `ruff` clean on
  every phase, **no CSV export anywhere yet** (0 endpoints, 0 buttons), no `pytest-cov`/mypy
  installed, `scripts/seed.py` exists (demo team + monitors), empty states/toasts/skeletons exist
  since Phase 4, no Monitor Detail page (Dashboard table is the only monitor UI — CSV buttons go
  there, one per row, plus one on the Incidents page).
- Locked scope for Phase 8 (4 builds, nothing more):
  - 8.1 CSV backend: `GET /monitors/{id}/checks/export?from&to` + `GET /incidents/export?status`
    (team-scoped, `StreamingResponse text/csv`, 50k-row cap, `Content-Disposition` filenames).
  - 8.2 CSV frontend: per-row download on Dashboard + Export button on Incidents (blob download).
  - 8.3 Coverage: add `pytest-cov` (dev-only), measure `--cov=app`, fill cheapest real gaps first,
    report the honest number (target 80%; mypy + pre-commit explicitly deferred — see below).
  - 8.4 Polish + docs: seed-data check, responsive spot-check, README + diary. No new features.
- Deferred with reasons (see chat 2026-09-18): mypy (dynamic codebase, high churn for low value
  now — ruff + 76 tests are the gates) and pre-commit hooks (no GitHub remote yet; nothing to
  protect). Both stay backlog, not silently dropped.
- Next actions in order: 8.1 CSV backend → 8.2 CSV frontend → 8.3 coverage → 8.4 polish+docs.

### 8.1 — CSV backend: streaming exports (DONE 2026-09-18)
- Created `app/services/export_service.py` — chunked generators (2,000-row SELECTs, flat memory),
  50,000-row cap, `csv` module quoting (commas/newlines in error text survive round-trip).
  Offset bug caught + fixed before shipping (varying LIMIT breaks page math → constant LIMIT +
  slice-to-cap). Added `incident_repository.page_for_team()` chunked reader.
- `GET /monitors/{id}/checks/export?from&to` (monitors.py) + `GET /incidents/export?status`
  (incidents.py) — `StreamingResponse text/csv` + `Content-Disposition` filenames, team-scoped
  (cross-team → 404; incidents export returns header-only for strangers).
- Real bug found by testing: `/incidents/export` registered AFTER `/{incident_id}` → "export" hit
  the UUID converter → 422. Fixed by defining `/export` FIRST (documented in docstring).
- Verified E2E (test DB): headers, quoting, filters, isolation; `ruff` clean.

### 8.2 — CSV frontend (DONE 2026-09-18)
- `src/lib/api.ts` — `downloadCsv()` (blob + object URL + auto filename, skips JSON unwrap).
- Dashboard monitor rows: `CSV` button (per-monitor filename). Incidents page: `Export CSV` button
  next to filters (respects OPEN/ACK/RESOLVED filter). Both toast on failure.
- Verified: `npm run build` green, `lint` 0 errors.

### 8.3 — Coverage: broken speedometer, honest 88% (DONE 2026-09-18)
- Added `pytest-cov` (dev-only). First measurement: **58%** — disbelieved (tests POST monitors yet
  `monitor_service.create_monitor` showed 0%). Proved with experiments: annotate showed impossible
  misses (line after executed line missed) → planted `raise PROBE_MARKER` → test FAILED on it,
  proving tests DO execute the file while coverage reports they don't. Root cause: SQLAlchemy
  asyncio runs DB I/O in greenlets, invisible to coverage's default tracer on this setup.
- Fix: `[tool.coverage.run] concurrency = ["thread", "greenlet"]` in `pyproject.toml`
  (source + omit documented). Re-measured: **66%** honest baseline.
- Gap-fill (36 new tests): `test_telegram_flow.py` (13: sender ok/429/timeout/fail, links,
  channels CRUD, connect/cancel/cross-team, poller dedupe+offset), `test_status_live.py` (6:
  privacy/cache/levels, live helpers, WS auth), `test_alerts.py` (7: open/recovery/escalation,
  skips, alerter schedule+dedupe, sweep), `test_heartbeats.py` (4: CRUD, ping/recovery, checker),
  `test_export.py` (3: quoting/disposition/filters/isolation), `test_flows.py` (3: maintenance,
  ack flows, root/health).
- Real bugs found by the new tests (all fixed): sweep-test asserted logs that only exist after
  sending (sweep only enqueues); heartbeat router imported redis inside the function (untestable
  binding → moved to top-level); global redis client loop-poisoning across pytest-asyncio's fresh
  loops (router now patched to test redis; TestSystem 503 → 200 in every order).
- Final: **112 passed, 88% coverage** (345 lines uncovered: WS socket loop ~56, retry/edge paths,
  lifespan, settings config — documented, not hidden). Target 80% beaten honestly.

### 8.4 — Polish + docs (DONE 2026-09-18)
- Seed: `scripts/seed.py` intact; demo login verified live (200) during Phase 6/7 smokes.
- Empty states/toasts/skeletons/mobile: inherited from Phase 4 premium UI (verified visually by
  user in Phases 4–6 screenshots); no changes needed, no new features added (scope discipline).
- `README.md` — Phase 8 header + API table (+2 CSV rows), CSV/coverage/test-count paragraphs
  (76 → **112 tests, 88%**).

---

# PHASE 9 — Docker Prod + CI/CD (IN PROGRESS — started 2026-09-18)

**Goal (roadmap Phase 9):** stop deploying by hand from a laptop — production-grade images,
green-gated pushes, one-command Northflank deploy. No product features.

> Diary follows chronologically — one entry per action. No code written yet (kickoff only).

### 9.0 — Kickoff + state read (2026-09-18)
- Read current state: `backend/Dockerfile` is dev-grade ON PURPOSE (root user, no healthcheck,
  `--reload` comes from compose, header comment says "Phase 9 replaces this"); `.dockerignore`
  already excludes `.venv/__pycache__/.env/.git`; NO project `.github/` dir (zero CI);
  `docker-compose.yml` is dev-only (volume mounts, baked dev JWT); git has 6 commits, ALL from
  Phases 0–3 — Phases 4–8 (Telegram, WS, heartbeats, AI, keys, webhooks, CSV, 112 tests) are
  UNCOMMITTED in the working tree; no GitHub remote yet (can't push/CI without it).
- Locked scope for Phase 9 (5 builds, nothing more):
  - 9.1 Git hygiene: commit Phases 4–8 as organized per-phase commits (history must tell the story).
  - 9.2 Prod image: hardened `Dockerfile` (non-root `appuser`, no reload, `HEALTHCHECK`,
    prod-only layers) + `docker-compose.prod.yml` (no volumes, env-driven, migrate step).
  - 9.3 CI: `.github/workflows/ci.yml` — ruff → pytest (Postgres+Redis services) → docker build.
    Branch protection explained (needs GitHub repo first).
  - 9.4 Northflank deploy pack: exact service definitions (api+worker start cmds, env table,
    migration step) as `DEPLOY.md` + verified `docker compose -f docker-compose.prod.yml` dry-run.
  - 9.5 README + diary. Frontend needs no Docker (Vercel builds from git).
- Needs from user (see chat 2026-09-18): create the GitHub repo + tell me its URL (I can't push
  or enable Actions without it); Northflank account when we reach 9.4.
- User gave `https://github.com/vineoy/pulsetrack-ai` + asked for a favicon, then `go`.
- Next actions in order: favicon → 9.1 commits → 9.2 images → 9.3 CI → 9.4 deploy pack → 9.5 docs.

### Favicon (DONE 2026-09-18)
- `frontend/public/favicon.svg` was still the default Vite lightning. Replaced with PulseTrack
  mark (indigo rounded square + white P + emerald status dot); `index.html` title
  `frontend` → `PulseTrack AI — Uptime Monitoring`. Build green, `dist/favicon.svg` confirmed.

### 9.1 — Git hygiene: remote + story-telling history + push (DONE 2026-09-18)
- `git remote add origin https://github.com/vineoy/pulsetrack-ai.git`. Verified `.env` +
  `backend/.env` gitignored (check-ignore) — no secrets committed.
- Problem: Phases 4–8 lived only in the working tree (last commit was Phase 3). Committed as
  5 grouped commits (Phase 4 backend / Phase 5 live+heartbeat / Phase 6 AI / Phase 7 platform+team /
  Phase 8 CSV+coverage) + favicon commit. Honest caveat (in each message + here): retroactive
  file-grouping, so intermediate commits may not boot standalone — only HEAD is verified green.
  From Phase 9 on, commits go per-phase live (CI enforces green main).
- `git push -u origin main` → `main -> main` live. One garbled-command hiccup (aborted, nothing
  staged) + one wrong-path hiccup (`backend/app/pyproject.toml` → `backend/pyproject.toml`);
  both recovered cleanly, verified via `git status`/`git log` after each step.

### 9.2 — Prod image + compose + dry-run (DONE 2026-09-18)
- Created `backend/Dockerfile.prod` (multi-stage: deps layer cached on lockfile, runtime layer on
  code; `appuser` non-root; stdlib-only HEALTHCHECK on `$PORT/health`; `uv sync --frozen --no-dev`
  so pytest/ruff never ship). Dev `Dockerfile` untouched.
- Created `docker-compose.prod.yml` (api :8001 + worker + `migrate` one-shot with
  `service_completed_successfully` gate; env-driven for Neon/Upstash; dev defaults point at
  host-mapped dev DB via `host.docker.internal`). Fixed a redundant `command` next to migrate's
  `entrypoint` before running.
- Dry-run vs dev DB (idempotent, safe): image builds; `migrate` exit 0; prod api answers
  `/health ok` as `appuser`; worker boots all 10 functions; stack torn down, dev `:8000` untouched.

### 9.3 — GitHub Actions CI (DONE 2026-09-18)
- Created `.github/workflows/ci.yml` (push/PR): backend job (ruff → pytest on Postgres 16
  port-mapped to **5433** to match test URLs + Redis 7), frontend job (Node 24 per `.nvmrc`,
  `npm ci` + lint + build), docker job (prod image build, needs backend+frontend green).
  Zero secrets required (tests mock Telegram/Gemini). YAML parse-verified.

### 9.4 — Northflank DEPLOY.md (DONE 2026-09-18)
- Created `DEPLOY.md`: accounts table, api/worker service definitions (same image, two start
  commands, full env table with JWT generation command), migrate-before-traffic rule + local
  equivalent, Vercel settings, 4-step verify checklist, rollback note (migrations additive-only
  on upgrade path — confirmed: all drops live in `downgrade()` only).

### 9.5 — README + diary (DONE 2026-09-18)
- `README.md`: CI + python + docker badges, Phase 9 header, Gemini model name corrected
  (2.0-flash → 3.5-flash-lite), deploy paragraph links DEPLOY.md + ci.yml.
- This diary: 9.0 → 9.5 entries. Frontend needs no Docker (Vercel builds from git).

### 9.6 — CI red → green: dummy tokens for the test env (DONE 2026-09-18)
- First CI run: frontend ✅ 15s, backend ❌ 14 failed / 98 passed. Every failure was
  `TELEGRAM_BOT_TOKEN/GEMINI_API_KEY is not configured` — CI has no `.env` (gitignored by
  design), so the token guards tripped before the mocked transports were reached. Locally green
  only because the real `backend/.env` masked it. Classic "works on my laptop" CI catch.
- Fix (one place, `ci.yml` backend job `env`): dummy tokens/username. Mock transports still
  intercept all HTTP — nothing real is ever called. Deliberately NOT fixed by weakening the
  prod guards or rewriting 14 tests: env-provided test secrets are the standard pattern.
- Verified locally with dummy env (simulating CI): 37/37 previously-failing files green, then
  full suite **112 passed** + `ruff` clean. Committed + pushed (`7dbc592`); CI re-runs automatically.
