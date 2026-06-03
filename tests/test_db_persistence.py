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
async def test_event_persistence_creates_event_and_session(session_maker) -> None:
    processor = RetailEventProcessorService(
        session_maker=session_maker,
        event_repository=SQLAlchemyEventRepository(session_maker),
        session_repository=SQLAlchemySessionRepository(session_maker),
    )

    event = RetailEvent(
        idempotency_key="event-entry-1",
        store_id="store-1",
        camera_id="camera-entry",
        event_type=EventType.ENTRY,
        occurred_at=datetime.now(timezone.utc),
        visitor_id="VIS_abc123",  # Re-ID token
        track_id="track-1",
        confidence=0.95,  # Detection confidence
        is_staff=False,  # Staff flag
        payload={"door": "main"},
    )

    assert await processor.process(event) is True

    async with session_maker() as session:
        event_count = await session.scalar(select(func.count()).select_from(EventRecord))
        session_count = await session.scalar(select(func.count()).select_from(SessionRecord))

        # Retrieve records to assert fields
        db_event = (await session.execute(select(EventRecord).limit(1))).scalar()
        db_session = (await session.execute(select(SessionRecord).limit(1))).scalar()

    assert event_count == 1
    assert session_count == 1

    assert db_event is not None
    assert db_event.visitor_id == "VIS_abc123"
    assert db_event.is_staff is False
    assert db_event.confidence == 0.95
    assert db_event.metadata_json == {"queue_depth": None, "session_seq": None, "sku_zone": None}

    assert db_session is not None
    assert db_session.visitor_id == "VIS_abc123"
    assert db_session.is_staff is False

