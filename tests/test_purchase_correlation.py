import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
import uuid

from app.main import create_app
from app.core.dependencies import get_purchase_correlation_service
from app.db.models.session import SessionRecord
from app.db.models.event import EventRecord
from app.db.models.transaction import TransactionRecord

@pytest.mark.asyncio
async def test_purchase_correlation_funnel(session_maker):
    now = datetime.now(timezone.utc)
    
    s1_id = uuid.uuid4()
    s2_id = uuid.uuid4()
    s3_id = uuid.uuid4() # No billing
    
    sessions = [
        SessionRecord(session_id=s1_id, store_id="store-test", track_id="t1", entry_event_id=uuid.uuid4(), opened_at=now, status="active", is_staff=False),
        SessionRecord(session_id=s2_id, store_id="store-test", track_id="t2", entry_event_id=uuid.uuid4(), opened_at=now, status="active", is_staff=False),
        SessionRecord(session_id=s3_id, store_id="store-test", track_id="t3", entry_event_id=uuid.uuid4(), opened_at=now, status="active", is_staff=False),
    ]
    
    events = [
        # S1 enters zone and billing
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e1", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now + timedelta(minutes=1), session_id=s1_id, zone_id="aisle_1", is_staff=False, confidence=1.0),
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e2", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now + timedelta(minutes=2), session_id=s1_id, zone_id="billing", is_staff=False, confidence=1.0),
        
        # S2 enters zone and billing at the same time
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e3", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now + timedelta(minutes=1), session_id=s2_id, zone_id="aisle_1", is_staff=False, confidence=1.0),
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e4", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now + timedelta(minutes=2), session_id=s2_id, zone_id="billing", is_staff=False, confidence=1.0),
        
        # S3 enters zone only
        EventRecord(event_id=uuid.uuid4(), idempotency_key="e5", store_id="store-test", camera_id="c1", event_type="ZONE_ENTER", occurred_at=now + timedelta(minutes=1), session_id=s3_id, zone_id="aisle_1", is_staff=False, confidence=1.0),
    ]
    
    # 1 transaction at min 4 (belongs to S1 because S1 and S2 hit billing at min 2, S1 is first or arbitrary but only 1 matches)
    # Wait, let's offset S2 by 1 second to make it deterministic
    events[3].occurred_at = now + timedelta(minutes=2, seconds=1)
    
    transactions = [
        TransactionRecord(transaction_id="tx-1", store_id="store-test", timestamp=now + timedelta(minutes=4), basket_value_inr=100.0)
    ]
    
    async with session_maker() as session:
        session.add_all(sessions)
        session.add_all(events)
        session.add_all(transactions)
        await session.commit()
        
    app = create_app()
    
    def override_get_correlation_service():
        from app.infrastructure.repositories.analytics import AnalyticsRepository
        from app.services.purchase_correlation import PurchaseCorrelationService
        repo = AnalyticsRepository(session_maker)
        return PurchaseCorrelationService(repository=repo)
        
    app.dependency_overrides[get_purchase_correlation_service] = override_get_correlation_service
    
    transport = ASGITransport(app=app)
    
    start_time_str = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time_str = (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/analytics/correlation/funnel?store_id=store-test&start_time={start_time_str}&end_time={end_time_str}")
        
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["entry"] == 3
    assert data["zone_visit"] == 3
    assert data["billing"] == 2
    assert data["purchase"] == 1
    assert data["conversion_rate"] == round(1 / 3, 4)
