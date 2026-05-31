from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.config import get_settings
from app.core.dependencies import get_container
from app.core.store_config import StoreConfigLoader
from app.domain.container import AppContainer
from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import AnomalyResponse, FunnelResponse, HeatmapResponse, MetricsResponse
from app.services.analytics_service import AnomalyService, FunnelService, HealthService, HeatmapService, MetricsService

router = APIRouter(prefix="/stores/{store_id}")


def _repository(container: AppContainer) -> AnalyticsRepository:
    return AnalyticsRepository(container.session_maker)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(store_id: str, container: AppContainer = Depends(get_container)) -> MetricsResponse:
    service = MetricsService(_repository(container))
    return await service.get_metrics(store_id)


@router.get("/funnel", response_model=FunnelResponse)
async def get_funnel(store_id: str, container: AppContainer = Depends(get_container)) -> FunnelResponse:
    service = FunnelService(_repository(container))
    return await service.get_funnel(store_id)


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(store_id: str, container: AppContainer = Depends(get_container)) -> HeatmapResponse:
    service = HeatmapService(_repository(container))
    return await service.get_heatmap(store_id)


@router.get("/anomalies", response_model=AnomalyResponse)
async def get_anomalies(store_id: str, container: AppContainer = Depends(get_container)) -> AnomalyResponse:
    store_config = StoreConfigLoader(container.settings.store_config_dir).load(store_id)
    service = AnomalyService(_repository(container), store_config=store_config)
    return await service.get_anomalies(store_id)
