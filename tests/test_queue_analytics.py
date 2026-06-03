import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import create_app
from app.db.models.session import SessionRecord
from app.db.models.event import EventRecord
from app.db.models.transaction import TransactionRecord
from app.core.dependencies import get_queue_analytics_service

@pytest.mark.asyncio
async def test_queue_analytics_metrics(session_maker):
    now = datetime.now(timezone.utc)
    
    s1_id = uuid.uuid4()
    s2_id = uuid.uuid4()
    s3_id = uuid.uuid4() # baseline session
    
    sessions = [
        SessionRecord(session_id=s1_id, store_id="store-test", track_id="t1", entry_event_id=uuid.uuid4(), opened_at=now, status="active", is_staff=False),
        SessionRecord(session_id=s2_id, store_id="store-test", track_id="t2", entry_event_id=uuid.uuid4(), opened_at=now, status="active", is_staff=False),
        SessionRecord(session_id=s3_id, store_id="store-test", track_id="t3", entry_event_id=uuid.uuid4(), opened_at=now - timedelta(hours=1), status="active", is_staff=False),
    ]
    
    events = [
        # s3 entered billing zone before our window
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e0", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now - timedelta(minutes=15), session_id=s3_id, zone_id="billing", is_staff=False, confidence=1.0),
        
        # s1 enters at min 1
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e1", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now + timedelta(minutes=1), session_id=s1_id, zone_id="billing", is_staff=False, confidence=1.0),
        
        # s2 enters at min 2
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e2", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now + timedelta(minutes=2), session_id=s2_id, zone_id="billing", is_staff=False, confidence=1.0),
        
        # s3 exits at min 3
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e3", store_id="store-test", camera_id="c1", event_type="ZONE_EXIT", occurred_at=now + timedelta(minutes=3), session_id=s3_id, zone_id="billing", is_staff=False, confidence=1.0),
        
        # s1 exits at min 4
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e4", store_id="store-test", camera_id="c1", event_type="ZONE_EXIT", occurred_at=now + timedelta(minutes=4), session_id=s1_id, zone_id="billing", is_staff=False, confidence=1.0),
        
        # s2 stays in queue (no exit)
    ]
    
    transactions = [
        # s1 makes a purchase at min 5
        TransactionRecord(transaction_id="tx-1", store_id="store-test", timestamp=now + timedelta(minutes=5), basket_value_inr=100.0)
    ]
    
    async with session_maker() as session:
        session.add_all(sessions)
        session.add_all(events)
        session.add_all(transactions)
        await session.commit()
        
    app = create_app()
    
    def override_get_queue_service():
        from app.infrastructure.repositories.analytics import AnalyticsRepository
        from app.services.queue_analytics import QueueAnalyticsService
        repo = AnalyticsRepository(session_maker)
        return QueueAnalyticsService(repository=repo)
        
    app.dependency_overrides[get_queue_analytics_service] = override_get_queue_service
    
    transport = ASGITransport(app=app)
    
    start_time_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time_str = (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/analytics/queue/metrics?store_id=store-test&start_time={start_time_str}&end_time={end_time_str}")
        
    assert response.status_code == 200, response.text
    data = response.json()
    
    # baseline=1 (s3), entries=2 (s1, s2)
    assert data["queue_entries"] == 2
    
    # exits=2 (s3, s1)
    assert data["queue_exits"] == 2
    
    # s1 waited 3 mins, s3 exit time isn't fully measurable (no enter time in window). Wait, our code excludes s3 from wait time.
    # So only s1's wait time (3 mins = 180s) is calculated.
    assert data["avg_wait_time_seconds"] == 180.0
    
    # s1 purchased. s3 abandoned. s2 still in queue.
    # Total resolved = 1 purchase (s1) + 1 abandonment (s3) = 2.
    # Abandonment rate = 1 / 2 = 0.5
    assert data["abandonment_count"] == 1
    assert data["abandonment_rate"] == 0.5
    
    # current_queue_size at end = 1 (s2)
    assert data["current_queue_size"] == 1
    
    # peak_queue_size:
    # start = 1
    # min 1 = 2 (s1 enters)
    # min 2 = 3 (s2 enters) -> PEAK
    # min 3 = 2 (s3 exits)
    # min 4 = 1 (s1 exits)
    assert data["peak_queue_size"] == 3
