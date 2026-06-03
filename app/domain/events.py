from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


class EventMetadata(BaseModel):
    """Metadata for retail events including queue and session info."""

    model_config = ConfigDict(extra="forbid")

    queue_depth: int | None = Field(default=None, ge=0)  # integer; null for non-billing events
    sku_zone: str | None = Field(default=None, min_length=1)  # zone label from store_layout.json
    session_seq: int | None = Field(default=None, ge=1)  # ordinal position in visitor session


class RetailEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    event_id: UUID = Field(default_factory=uuid4)
    idempotency_key: str | None = Field(default=None, min_length=1)
    store_id: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    event_type: EventType
    occurred_at: datetime
    visitor_id: str | None = Field(default=None, min_length=1)  # Re-ID token - unique per visit session
    track_id: str | None = Field(default=None, min_length=1)  # Camera-specific track ID
    zone_id: str | None = Field(default=None, min_length=1)  # null for ENTRY / EXIT events
    dwell_ms: int | None = Field(default=None, ge=0)  # duration in ms; 0 for instantaneous events
    is_staff: bool = Field(default=False)  # model must classify this
    confidence: float = Field(ge=0.0, le=1.0)  # detection confidence - do not suppress low-conf events
    session_id: UUID | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    metadata: EventMetadata = Field(default_factory=EventMetadata)  # queue_depth, sku_zone, session_seq
    trace_id: str | None = Field(default=None, min_length=1)

    @field_validator("idempotency_key")
    @classmethod
    def _normalize_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("idempotency_key cannot be blank")
        return normalized

    @field_validator("trace_id")
    @classmethod
    def _normalize_trace_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("trace_id cannot be blank")
        return normalized


class RetailEventEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event: RetailEvent
