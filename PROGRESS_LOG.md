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

## Next: Phase 4 — Alerts + Escalation + Maintenance
notification_channels + alert_logs + maintenance_windows models (migration 004), Resend email +
generic webhook sender with 3x retry/backoff, alert on OPEN / recovery mail on RESOLVE,
escalate if OPEN 10min unacked, skip when in maintenance window, channels UI + Test button.
