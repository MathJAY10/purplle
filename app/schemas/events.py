from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.events import EventType, EventMetadata


class RetailEventIngestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    idempotency_key: str | None = Field(default=None, min_length=1)
    store_id: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    event_type: EventType
    occurred_at: datetime
    visitor_id: str | None = Field(default=None, min_length=1)  # Re-ID token
    track_id: str | None = Field(default=None, min_length=1)  # Camera-specific track ID
    zone_id: str | None = Field(default=None, min_length=1)  # null for ENTRY / EXIT
    dwell_ms: int | None = Field(default=None, ge=0)  # duration in ms
    is_staff: bool = Field(default=False)  # staff flag
    confidence: float = Field(ge=0.0, le=1.0)  # detection confidence
    session_id: UUID | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    metadata: EventMetadata = Field(default_factory=EventMetadata)  # queue_depth, sku_zone, session_seq


class EventIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[RetailEventIngestItem] = Field(min_length=1)


class EventIngestResponse(BaseModel):
    accepted: int
    event_ids: list[UUID]
    duplicate_event_ids: list[UUID] = Field(default_factory=list)
