import ssl
from collections.abc import AsyncGenerator

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def resolve_database_config(url_str: str) -> tuple[str, dict]:
    """Split a DATABASE_URL into (clean_url, connect_args).

    Managed Postgres (Neon) requires TLS but asyncpg rejects libpq-style
    `?sslmode=` query params. So: pop `sslmode` out of the URL and translate it
    into an SSLContext instead. No `sslmode` (local Docker) → unchanged behavior.
    """
    url = make_url(url_str)
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
