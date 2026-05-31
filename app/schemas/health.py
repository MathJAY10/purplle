from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: Literal["ok", "down"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    environment: str
    version: str
    timestamp: datetime
    database: ComponentHealth
    redis: ComponentHealth
    last_event_timestamp: datetime | None = None
    stale_feed: bool = False
