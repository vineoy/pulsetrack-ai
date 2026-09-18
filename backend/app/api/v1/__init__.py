from fastapi import APIRouter

from app.api.v1.routers import (
    ai,
    api_keys,
    audit,
    auth,
    heartbeats,
    incidents,
    maintenance,
    monitors,
    notification_channels,
    status,
    teams,
    webhooks,
)
from app.core.config import get_settings

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(ai.router)
api_router.include_router(api_keys.router)
api_router.include_router(audit.router)
api_router.include_router(auth.router)
api_router.include_router(teams.router)
api_router.include_router(monitors.router)
api_router.include_router(notification_channels.router)
api_router.include_router(maintenance.router)
api_router.include_router(incidents.router)
api_router.include_router(status.router)
api_router.include_router(heartbeats.router)
api_router.include_router(webhooks.router)
