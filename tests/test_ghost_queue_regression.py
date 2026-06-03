import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.db.models.event import EventRecord
from app.db.models.session import SessionRecord
from app.domain.events import RetailEvent, EventType, EventMetadata
from app.services.event_processor_service import RetailEventProcessorService
from app.infrastructure.repositories.events import SQLAlchemyEventRepository
from app.infrastructure.repositories.sessions import SQLAlchemySessionRepository
from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.services.queue_analytics import QueueAnalyticsService

@pytest.mark.asyncio
async def test_ghost_queue_regression_fix(session_maker):
    """
    Test that publishing ZONE_EXIT before EXIT guarantees the ZONE_EXIT
    is attached to the correct active session.
    """
    event_repo = SQLAlchemyEventRepository(session_maker)
    session_repo = SQLAlchemySessionRepository(session_maker)
    analytics_repo = AnalyticsRepository(session_maker)
    
    processor = RetailEventProcessorService(
        session_maker=session_maker,
        event_repository=event_repo,
        session_repository=session_repo
    )
    
    queue_service = QueueAnalyticsService(repository=analytics_repo)
    
    visitor_id = "test-visitor-ghost-regression"
    store_id = "test-store"
    camera_id = "cam-1"
    
    now = datetime.now(timezone.utc)
    
    # 1. Visitor enters store (ENTRY)
    entry_event = RetailEvent(
        store_id=store_id,
        camera_id=camera_id,
        event_type=EventType.ENTRY,
        occurred_at=now,
        visitor_id=visitor_id,
        track_id="t1",
        confidence=1.0,
        metadata=EventMetadata()
    )
    await processor.process(entry_event)
    
    # Verify session is active
    async with session_maker() as session:
        active_session = await session_repo.get_active_by_store_and_visitor(session, store_id, visitor_id)
        assert active_session is not None
        session_id = active_session.session_id
        
    # 2. Visitor enters billing zone (ZONE_ENTER)
    zone_enter_event = RetailEvent(
        store_id=store_id,
        camera_id=camera_id,
        event_type=EventType.ZONE_ENTER,
        occurred_at=now + timedelta(minutes=1),
        visitor_id=visitor_id,
        zone_id="billing",
        confidence=1.0,
        metadata=EventMetadata()
    )
    await processor.process(zone_enter_event)
    
    # 3. Ghost Queue Sequence (The fix):
    # In processor.py, the order is now:
    #   a) ZONE_EXIT (synthetic)
    #   b) EXIT
    synthetic_zone_exit = RetailEvent(
        store_id=store_id,
        camera_id=camera_id,
        event_type=EventType.ZONE_EXIT,
        occurred_at=now + timedelta(minutes=2),
        visitor_id=visitor_id,
        zone_id="billing",
        confidence=1.0,
        metadata=EventMetadata()
    )
    
    exit_event = RetailEvent(
        store_id=store_id,
        camera_id=camera_id,
        event_type=EventType.EXIT,
        occurred_at=now + timedelta(minutes=2),
        visitor_id=visitor_id,
        track_id="t1",
        confidence=1.0,
        metadata=EventMetadata()
    )
    
    # Simulate processing them in the new order (ZONE_EXIT first, then EXIT)
    await processor.process(synthetic_zone_exit)
    await processor.process(exit_event)
    
    # 4. Verification
    async with session_maker() as session:
        # Check if the session is closed
        stmt = select(SessionRecord).where(SessionRecord.session_id == session_id)
        s_rec = (await session.execute(stmt)).scalar_one()
        assert s_rec.status == "closed"
        
        # Check if ZONE_EXIT got the valid session_id
        stmt = select(EventRecord).where(
            EventRecord.visitor_id == visitor_id,
            EventRecord.event_type == "ZONE_EXIT"
        )
        z_exit_rec = (await session.execute(stmt)).scalar_one()
        
        # CRITICAL ASSERTION: The session_id must not be NULL!
        assert z_exit_rec.session_id == session_id
        
    # 5. Check Queue Analytics
    metrics = await queue_service.get_queue_metrics(
        store_id=store_id,
        start_time=now - timedelta(minutes=10),
        end_time=now + timedelta(minutes=10)
    )
    
    # Queue entries should be 1
    assert metrics["queue_entries"] == 1
    # Queue exits should be 1
    assert metrics["queue_exits"] == 1
    # The queue occupancy should correctly return to zero at the end
    assert metrics["current_queue_size"] == 0
