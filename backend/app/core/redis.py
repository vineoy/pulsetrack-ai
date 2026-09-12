from redis import asyncio as aioredis

from app.core.config import get_settings

redis_client = aioredis.from_url(get_settings().redis_url, decode_responses=True)


def get_redis() -> aioredis.Redis:
    """Dependency so tests can swap in a clean Redis database."""
    return redis_client
