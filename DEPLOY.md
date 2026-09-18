# Deploy to production — Northflank + Neon + Upstash + Vercel ($0/mo)

One image (`backend/Dockerfile.prod`), two always-on Sandbox services, external
free Postgres/Redis. CI must be green on `main` before you deploy.

## 0. One-time accounts (all free)

| Service | Use | Free tier note |
|---|---|---|
| Northflank | `api` + `worker` Sandbox services | 2 always-on services, no sleep |
| Neon | Postgres 16 | Permanent free, pooled connection string |
| Upstash | Redis | Persistent free |
| Vercel | Frontend | Builds `frontend/` from git |
| Telegram | `@BotFather` token + username | Already have |
| Google AI Studio | `GEMINI_API_KEY` | Already have |

## 1. Backend on Northflank (same image, twice)

Create a Northflank project from GitHub repo `vineoy/pulsetrack-ai`, then two
**combined services** with Dockerfile path `backend/Dockerfile.prod`
(build context = repo root):

| | `api` | `worker` |
|---|---|---|
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | `arq app.workers.settings.WorkerSettings` |
| Port | `$PORT` (http, health path `/health`) | none (background) |

Both services share these env vars (set once in Northflank, never in git):

```
ENVIRONMENT=production
DATABASE_URL=<Neon pooled URL, postgresql://...?sslmode=require>
REDIS_URL=<Upstash URL, rediss://...>
JWT_SECRET=<random 48 chars: python -c "import secrets; print(secrets.token_urlsafe(48))">
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_BOT_USERNAME=<bot username, no @>
TELEGRAM_ESCALATION_DELAY_MIN=10
TELEGRAM_LINK_EXPIRE_MIN=15
GEMINI_API_KEY=<from AI Studio>
GEMINI_MODEL=gemini-3.5-flash-lite
```

## 2. Migrate BEFORE new code serves (every deploy)

New code + old tables = 500s. Run once per deploy, before traffic hits:

- Northflank **Job** (same image + env): `alembic upgrade head`
- Local equivalent (what CI dry-runs):
  `docker compose -f docker-compose.prod.yml --env-file .env up migrate`

## 3. Frontend on Vercel

Import the repo → root directory `frontend/` → env `VITE_API_URL=https://<your-northflank-api>`.
Deploys automatically on every `main` push.

## 4. Verify (2-minute checklist)

1. `GET https://<api>/health` → `{"status":"ok","db":"up","redis":"up"}`
2. Worker logs show all 10 functions (check, telegram×2, poller, heartbeat,
   webhook + 4 crons).
3. Add a monitor → kill its URL → 🔴 Telegram in ~2 min → `/s/<slug>` red in
   incognito → fix URL → 🟢 recovery.
4. Settings → Connect Telegram → Start → ✅ (poller cron, no SSH needed).

## 5. Rollback

Northflank → service → previous build → redeploy (image tags are per-commit).
If a migration already ran, the old code must tolerate new columns (all Phase
0–8 migrations are additive-only: new tables/columns, never drops/renames).
