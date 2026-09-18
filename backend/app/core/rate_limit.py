"""Tiny fixed-window rate limiter on Redis (Phase 6: AI 10/min/user).

No middleware, no new dependency — endpoints call check_rate_limit() directly.
Redis down → fail OPEN (AI stays usable locally; Upstash is reliable in prod).
"""

from app.core.exceptions import AppError


async def check_rate_limit(
    redis, *, key: str, limit: int, window_sec: int
) -> None:
    """Allow `limit` hits per `window_sec`. Raises 429 AppError when exceeded."""
    try:
        hits = await redis.incr(key)
        if hits == 1:
            await redis.expire(key, window_sec)
            return
        if hits > limit:
            raise AppError(
                429,
                "RATE_LIMITED",
                f"Too many requests — try again in under a minute ({limit}/min).",
                headers={"Retry-After": str(window_sec)},
            )
    except AppError:
        raise
    except Exception:  # noqa: BLE001
        # Redis blip: don't block the user for a counter failure.
        return
