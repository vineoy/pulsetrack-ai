import pytest
from httpx import ASGITransport, AsyncClient
from redis import asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import get_db
from app.core.redis import get_redis
from app.main import app
from app.models import Base

# Tests run against the SAME docker-compose Postgres/Redis, but in a separate
# database (pulsetrack_test) and Redis DB number (1) so dev data is never touched.
ADMIN_DB_URL = "postgresql+psycopg://pulse:pulse@localhost:5433/postgres"
TEST_DB_URL = "postgresql+psycopg://pulse:pulse@localhost:5433/pulsetrack_test"
TEST_REDIS_URL = "redis://localhost:6379/1"


async def _ensure_test_database() -> None:
    # Check existence first: CREATE DATABASE cannot run inside a transaction and
    # psycopg's "already exists" error arrives wrapped by SQLAlchemy, not catchable.
    check_engine = create_async_engine(ADMIN_DB_URL)
    create_engine = create_async_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    try:
        async with check_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = 'pulsetrack_test'")
            )
        if not exists:
            async with create_engine.connect() as conn:
                await conn.execute(text("CREATE DATABASE pulsetrack_test"))
    finally:
        await check_engine.dispose()
        await create_engine.dispose()


@pytest.fixture
async def db_engine():
    await _ensure_test_database()
    engine = create_async_engine(TEST_DB_URL)
    # Fresh schema per test: slow-ish but bulletproof isolation between tests.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def redis_client():
    client = aioredis.from_url(TEST_REDIS_URL, decode_responses=True)
    await client.flushdb()
    yield client
    await client.aclose()


@pytest.fixture
async def client(db_session, redis_client):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = lambda: redis_client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    app.dependency_overrides.clear()
