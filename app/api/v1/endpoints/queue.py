from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_queue_analytics_service
from app.services.queue_analytics import QueueAnalyticsService

router = APIRouter(prefix="/analytics/queue", tags=["queue"])

@router.get("/metrics")
async def get_queue_metrics(
    store_id: str = Query(...),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    service: QueueAnalyticsService = Depends(get_queue_analytics_service),
):
    now = datetime.now(timezone.utc)
    if not end_time:
        end_time = now
    if not start_time:
        start_time = end_time - timedelta(days=7)
        
    return await service.get_queue_metrics(
        store_id=store_id, 
        start_time=start_time, 
        end_time=end_time
    )
