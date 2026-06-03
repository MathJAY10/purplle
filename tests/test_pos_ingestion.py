import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import zoneinfo

from app.main import create_app
from httpx import ASGITransport
from app.core.dependencies import get_pos_ingestion_service
from app.services.pos_ingestion import POSIngestionService
from app.infrastructure.repositories.transactions import SQLAlchemyTransactionRepository
from app.db.models.transaction import TransactionRecord

@pytest.mark.asyncio
async def test_upload_pos_transactions_csv(session_maker):
    csv_content = (
        "transaction_id,store_id,timestamp,basket_value_inr\n"
        "TXN-001,store-001,2026-06-03T10:00:00Z,150.50\n"
        "TXN-002,store-001,2026-06-03T10:15:00Z,400.00\n"
    )
    
    app = create_app()
    
    # Use dependency override to inject our test session_maker
    def override_get_pos_service():
        repo = SQLAlchemyTransactionRepository(session_maker=session_maker)
        return POSIngestionService(session_maker=session_maker, repository=repo)
        
    app.dependency_overrides[get_pos_ingestion_service] = override_get_pos_service
    
    transport = ASGITransport(app=app)
    files = {"file": ("test_transactions.csv", csv_content, "text/csv")}
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/pos/transactions/upload", files=files, data={"store_timezone": "UTC"})
        
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["errors"] == 0
    
    # Verify DB insertion
    async with session_maker() as session:
        result = await session.execute(select(TransactionRecord))
        records = result.scalars().all()
        
    assert len(records) == 2
    
    txn_1 = next(r for r in records if r.transaction_id == "TXN-001")
    assert txn_1.store_id == "store-001"
    assert float(txn_1.basket_value_inr) == 150.50

@pytest.mark.asyncio
async def test_upload_pos_transactions_timezones(session_maker):
    csv_content = (
        "transaction_id,store_id,timestamp,basket_value_inr\n"
        "TXN-IST,store-001,2026-06-03 10:02:00,100.00\n"
        "TXN-UTC,store-001,2026-06-03T10:02:00Z,200.00\n"
        "TXN-OFF,store-001,2026-06-03T10:02:00+05:30,300.00\n"
    )
    
    app = create_app()
    
    def override_get_pos_service():
        repo = SQLAlchemyTransactionRepository(session_maker=session_maker)
        return POSIngestionService(session_maker=session_maker, repository=repo)
        
    app.dependency_overrides[get_pos_ingestion_service] = override_get_pos_service
    
    transport = ASGITransport(app=app)
    files = {"file": ("test_tz.csv", csv_content, "text/csv")}
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Use Asia/Kolkata timezone (+05:30)
        response = await client.post("/pos/transactions/upload", files=files, data={"store_timezone": "Asia/Kolkata"})
        
    assert response.status_code == 200
    
    # Verify DB insertion
    async with session_maker() as session:
        result = await session.execute(select(TransactionRecord))
        records = result.scalars().all()
        
    # Get the 3 transactions
    tx_ist = next(r for r in records if r.transaction_id == "TXN-IST")
    tx_utc = next(r for r in records if r.transaction_id == "TXN-UTC")
    tx_off = next(r for r in records if r.transaction_id == "TXN-OFF")
    
    # Test 3: Naive timestamp (2026-06-03 10:02:00) with store_timezone=Asia/Kolkata
    # 10:02:00 IST is 04:32:00 UTC
    assert tx_ist.timestamp.hour == 4
    assert tx_ist.timestamp.minute == 32
    
    # Test 2: UTC timestamp (2026-06-03T10:02:00Z)
    # Should remain 10:02:00 UTC
    assert tx_utc.timestamp.hour == 10
    assert tx_utc.timestamp.minute == 2
    
    # Test 4: Offset timestamp (2026-06-03T10:02:00+05:30)
    # 10:02:00 +05:30 is 04:32:00 UTC
    assert tx_off.timestamp.hour == 4
    assert tx_off.timestamp.minute == 32
