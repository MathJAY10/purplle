from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.dependencies import get_container
from app.domain.container import AppContainer
from app.schemas.health import ComponentHealth, HealthResponse
from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.services.analytics_service import HealthService

router = APIRouter(prefix="/health")


@router.get("", response_model=HealthResponse)
async def health_check(container: AppContainer = Depends(get_container)) -> HealthResponse:
    database = await _check_database(container)
    redis = await _check_redis(container)
    service_status = "ok" if database.status == "ok" and redis.status == "ok" else "degraded"
    repository = AnalyticsRepository(container.session_maker)
    health_service = HealthService(repository=repository, stale_feed_seconds=container.settings.health_stale_feed_seconds)
    details = await health_service.get_health(
        service_status=service_status,
        redis_status=redis.status,
        db_status=database.status,
        store_id="default-store",
    )

    return HealthResponse(
        status=service_status,
        service=container.settings.app_name,
        environment=container.settings.app_env,
        version=container.settings.app_version,
        timestamp=datetime.now(timezone.utc),
        database=database,
        redis=redis,
        last_event_timestamp=details["last_event_timestamp"],
        stale_feed=bool(details["stale_feed"]),
    )


async def _check_database(container: AppContainer) -> ComponentHealth:
    try:
        async with container.session_maker() as session:
            await session.execute(text("SELECT 1"))
        return ComponentHealth(status="ok")
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(status="down", detail=str(exc))


async def _check_redis(container: AppContainer) -> ComponentHealth:
    try:
        await container.redis.ping()
        return ComponentHealth(status="ok")
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(status="down", detail=str(exc))
