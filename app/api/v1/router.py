from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.events import router as events_router
from app.api.v1.endpoints.health import router as health_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(events_router, tags=["events"])
router.include_router(analytics_router, tags=["analytics"])
router.include_router(dashboard_router, tags=["dashboard"])
