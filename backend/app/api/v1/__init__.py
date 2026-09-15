from fastapi import APIRouter

from app.api.v1.routers import auth, monitors, teams
from app.core.config import get_settings

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(auth.router)
api_router.include_router(teams.router)
api_router.include_router(monitors.router)
