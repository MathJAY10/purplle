from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.events import EventType, RetailEvent
from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.infrastructure.repositories.events import SQLAlchemyEventRepository
from app.infrastructure.repositories.sessions import SQLAlchemySessionRepository
from app.services.analytics_service import FunnelService, HeatmapService, MetricsService
from app.services.event_processor_service import RetailEventProcessorService


async def _seed_events(session_maker) -> None:
    processor = RetailEventProcessorService(
        session_maker=session_maker,
        event_repository=SQLAlchemyEventRepository(session_maker),
        session_repository=SQLAlchemySessionRepository(session_maker),
    )
    entry = RetailEvent(
        idempotency_key="entry-1",
        store_id="store-1",
        camera_id="camera-entry",
        event_type=EventType.ENTRY,
        occurred_at=datetime.now(timezone.utc),
        visitor_id="VIS_test001",  # Re-ID token
        track_id="track-1",
        confidence=0.98,  # Detection confidence
        is_staff=False,  # Staff flag
        payload={"zone": "entry"},
    )
    exit_event = RetailEvent(
        idempotency_key="exit-1",
        store_id="store-1",
        camera_id="camera-entry",
        event_type=EventType.EXIT,
        occurred_at=datetime.now(timezone.utc),
        visitor_id="VIS_test001",  # Same visitor
        track_id="track-1",
        confidence=0.97,  # Detection confidence
        is_staff=False,  # Staff flag
        payload={"zone": "billing"},
    )
    await processor.process(entry)
    await processor.process(exit_event)


@pytest.mark.asyncio
async def test_metrics_service_calculates_store_metrics(session_maker) -> None:
    await _seed_events(session_maker)
    repository = AnalyticsRepository(session_maker)
    service = MetricsService(repository)

    metrics = await service.get_metrics("store-1")

    assert metrics.unique_visitors == 1
    assert metrics.conversion_rate == 1.0
    assert metrics.avg_dwell_time >= 0.0
    assert metrics.queue_depth >= 0


@pytest.mark.asyncio
async def test_funnel_service_builds_dropoff(session_maker) -> None:
    await _seed_events(session_maker)
    repository = AnalyticsRepository(session_maker)
    service = FunnelService(repository)

    funnel = await service.get_funnel("store-1")

    assert funnel.stages[0].stage == "ENTRY"
    assert funnel.stages[0].count == 1
    assert len(funnel.stages) == 4


@pytest.mark.asyncio
async def test_heatmap_service_returns_zone_scores(session_maker) -> None:
    await _seed_events(session_maker)
    repository = AnalyticsRepository(session_maker)
    service = HeatmapService(repository)

    heatmap = await service.get_heatmap("store-1")

    assert heatmap.store_id == "store-1"
    assert heatmap.zones
