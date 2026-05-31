from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    unique_visitors: int
    conversion_rate: float
    avg_dwell_time: float
    queue_depth: int
    abandonment_rate: float


class FunnelStage(BaseModel):
    stage: str
    count: int
    dropoff_percentage: float


class FunnelResponse(BaseModel):
    store_id: str
    stages: list[FunnelStage]


class HeatmapZoneResponse(BaseModel):
    zone: str
    visits: int
    avg_dwell_ms: float
    normalized_score: float


class HeatmapResponse(BaseModel):
    store_id: str
    zones: list[HeatmapZoneResponse]


class AnomalyResponseItem(BaseModel):
    anomaly_type: str
    severity: str
    description: str
    metric_value: float | None = None
    threshold_value: float | None = None
    observed_at: datetime


class AnomalyResponse(BaseModel):
    store_id: str
    anomalies: list[AnomalyResponseItem]


class HealthDetails(BaseModel):
    service_status: str
    redis_status: str
    db_status: str
    last_event_timestamp: datetime | None = None
    stale_feed: bool
