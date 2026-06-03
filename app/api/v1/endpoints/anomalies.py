from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.dependencies import get_anomaly_detection_service
from app.services.anomaly_detection import AnomalyDetectionService

router = APIRouter(prefix="/analytics/anomalies", tags=["anomalies"])

class AnomalyResponse(BaseModel):
    anomaly_id: str
    store_id: str
    anomaly_type: str
    severity: str
    description: str
    metric_value: float | None
    threshold_value: float | None
    observed_at: datetime
    metadata_json: dict[str, Any]

@router.post("/detect", response_model=list[AnomalyResponse])
async def detect_anomalies(
    store_id: str = Query(...),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    service: AnomalyDetectionService = Depends(get_anomaly_detection_service),
):
    now = datetime.now(timezone.utc)
    if not end_time:
        end_time = now
    if not start_time:
        start_time = end_time - timedelta(hours=1)
        
    records = await service.detect_and_record_anomalies(
        store_id=store_id,
        start_time=start_time,
        end_time=end_time
    )
    
    return [
        AnomalyResponse(
            anomaly_id=str(r.anomaly_id),
            store_id=r.store_id,
            anomaly_type=r.anomaly_type,
            severity=r.severity,
            description=r.description,
            metric_value=r.metric_value,
            threshold_value=r.threshold_value,
            observed_at=r.observed_at,
            metadata_json=r.metadata_json
        ) for r in records
    ]

@router.get("", response_model=list[AnomalyResponse])
async def get_anomalies(
    store_id: str = Query(...),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    service: AnomalyDetectionService = Depends(get_anomaly_detection_service),
):
    now = datetime.now(timezone.utc)
    if not end_time:
        end_time = now
    if not start_time:
        start_time = end_time - timedelta(days=7)
        
    records = await service.get_anomalies(
        store_id=store_id,
        start_time=start_time,
        end_time=end_time
    )
    
    return [
        AnomalyResponse(
            anomaly_id=str(r.anomaly_id),
            store_id=r.store_id,
            anomaly_type=r.anomaly_type,
            severity=r.severity,
            description=r.description,
            metric_value=r.metric_value,
            threshold_value=r.threshold_value,
            observed_at=r.observed_at,
            metadata_json=r.metadata_json
        ) for r in records
    ]
