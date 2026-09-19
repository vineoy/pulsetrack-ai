import ssl
import sys
from collections.abc import AsyncGenerator

if sys.platform == "win32":
    # psycopg (async) cannot run on Windows' default ProactorEventLoop —
    # force SelectorEventLoop process-wide. Linux (Docker/Northflank/CI) is
    # unaffected. Without this, every DB call fails on local Windows runs.
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def resolve_database_config(url_str: str) -> tuple[str, dict]:
    """Split a DATABASE_URL into (clean_url, connect_args).

    Driver-aware: psycopg speaks native libpq params (`?sslmode=`,
    `?channel_binding=` incl. SCRAM channel-binding auth that Neon requires),
    so its URLs pass through untouched. The legacy asyncpg path pops `sslmode`
    out and translates it into an SSLContext instead. No TLS params (local
    Docker) → unchanged behavior either way.
    """
    url = make_url(url_str)
    if "+psycopg" in url.drivername:
        return url_str, {}
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    connect_args: dict = {}
    if sslmode in ("require", "prefer", "verify-ca", "verify-full"):
        # Default context verifies the server cert (Neon presents a valid
        # public cert) — strictest option that works, no knobs to misconfigure.
        connect_args["ssl"] = ssl.create_default_context()
    clean_url = str(url.set(query=query)) if sslmode else url_str
    return clean_url, connect_args


_clean_url, _connect_args = resolve_database_config(settings.database_url)

engine = create_async_engine(_clean_url, connect_args=_connect_args, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """One session per request. FastAPI's dependency system closes it automatically."""
    async with async_session_factory() as session:
        yield session
