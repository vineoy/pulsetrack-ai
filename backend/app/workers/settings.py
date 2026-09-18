"""ARQ WorkerSettings - run with: arq app.workers.settings.WorkerSettings

The scheduler cron fires every 30s and enqueues due monitors; check_job does
the actual probing. One worker process runs both (ARQ workers execute cron
jobs and queued functions in the same loop).
"""

from collections.abc import Awaitable, Callable

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import get_settings
from app.workers.alerter import sweep_stale_escalations, telegram_alert_job, telegram_test_job
from app.workers.checker import check_job, enqueue_due_monitors
from app.workers.heartbeat_checker import heartbeat_checker
from app.workers.telegram_poller import poll_telegram_updates
from app.workers.webhooker import webhook_delivery_job

settings = get_settings()


async def on_startup(ctx: dict) -> None:
    ctx["config"] = {"redis_url": settings.redis_url}


async def on_shutdown(ctx: dict) -> None:
    pass


class WorkerSettings:
    functions = [
        check_job,
        telegram_alert_job,
        telegram_test_job,
        poll_telegram_updates,
        heartbeat_checker,
        webhook_delivery_job,
    ]
    cron_jobs: list[Callable[..., Awaitable]] = [
        # every 30 seconds: find monitors where next_check_at <= now, enqueue checks
        cron(enqueue_due_monitors, second={0, 30}, unique=True),
        # every minute: catch escalations missed due to Redis defer loss / worker sleep
        cron(sweep_stale_escalations, second={15}, unique=True),
        # every 30 seconds (offset by 10s): auto-connect Telegram via getUpdates polling
        cron(poll_telegram_updates, second={10, 40}, unique=True),
        # every minute: heartbeats silent past period+grace -> MISSING + Telegram
        cron(heartbeat_checker, second={20}, unique=True),
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    # A failed probe is retried by the next scheduled tick, not by ARQ retries.
    max_tries = 4
    job_timeout = 45  # seconds; keeps a stuck job from blocking the queue
    max_jobs = 20  # concurrent probes per worker process
