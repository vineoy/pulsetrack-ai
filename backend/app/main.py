from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Multi-tenant uptime monitoring SaaS with an AI incident analyst.",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["system"])
async def health() -> JSONResponse:
    """Liveness + dependency readiness. Used by Docker, CI and Render."""
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "up"
    except Exception:
        checks["db"] = "down"
    try:
        await redis_client.ping()
        checks["redis"] = "up"
    except Exception:
        checks["redis"] = "down"

    ok = all(v == "up" for v in checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", **checks},
    )
