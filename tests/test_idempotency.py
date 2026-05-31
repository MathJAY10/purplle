from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.db.models import EventRecord, SessionRecord
from app.domain.events import EventType, RetailEvent
from app.infrastructure.repositories.events import SQLAlchemyEventRepository
from app.infrastructure.repositories.sessions import SQLAlchemySessionRepository
from app.services.event_processor_service import RetailEventProcessorService


@pytest.mark.asyncio
async def test_duplicate_event_is_idempotent(session_maker) -> None:
    processor = RetailEventProcessorService(
        session_maker=session_maker,
        event_repository=SQLAlchemyEventRepository(session_maker),
        session_repository=SQLAlchemySessionRepository(session_maker),
    )

    event = RetailEvent(
        idempotency_key="event-entry-duplicate",
        store_id="store-1",
        camera_id="camera-entry",
        event_type=EventType.ENTRY,
        occurred_at=datetime.now(timezone.utc),
        track_id="track-1",
        payload={"door": "main"},
    )

    first_result = await processor.process(event)
    second_result = await processor.process(event)

    assert first_result is True
    assert second_result is False

    async with session_maker() as session:
        event_count = await session.scalar(select(func.count()).select_from(EventRecord))
        session_count = await session.scalar(select(func.count()).select_from(SessionRecord))

    assert event_count == 1
    assert session_count == 1
