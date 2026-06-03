from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_purchase_correlation_service
from app.services.purchase_correlation import PurchaseCorrelationService

router = APIRouter(prefix="/analytics/correlation", tags=["correlation"])

@router.get("/funnel")
async def get_purchase_funnel(
    store_id: str,
    start_time: datetime | None = Query(None, description="Start time for funnel analysis"),
    end_time: datetime | None = Query(None, description="End time for funnel analysis"),
    service: PurchaseCorrelationService = Depends(get_purchase_correlation_service)
):
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    if start_time is None:
        start_time = end_time - timedelta(days=7)
        
    # Ensure timezone info
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
        
    return await service.get_funnel_analytics(
        store_id=store_id,
        start_time=start_time,
        end_time=end_time
    )
