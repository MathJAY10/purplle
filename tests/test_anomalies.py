from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db.models.event import EventRecord
from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.services.analytics_service import AnomalyService


@pytest.mark.asyncio
async def test_anomaly_service_detects_queue_spike(session_maker) -> None:
    async with session_maker() as session:
        for index in range(11):
            session.add(
                EventRecord(
                    idempotency_key=f"event-{index}",
                    store_id="store-1",
                    camera_id="camera-1",
                    event_type="ENTRY",
                    occurred_at=datetime.now(timezone.utc),
                    payload={"zone": "billing"},
                )
            )
        await session.commit()

    repository = AnalyticsRepository(session_maker)
    service = AnomalyService(repository)

    anomalies = await service.get_anomalies("store-1")

    assert anomalies.store_id == "store-1"
    assert any(item.anomaly_type == "queue_spike" for item in anomalies.anomalies)
