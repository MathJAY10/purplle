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


class RetailEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    event_id: UUID = Field(default_factory=uuid4)
    idempotency_key: str | None = Field(default=None, min_length=1)
    store_id: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    event_type: EventType
    occurred_at: datetime
    track_id: str | None = Field(default=None, min_length=1)
    session_id: UUID | None = None
    payload: dict[str, object] = Field(default_factory=dict)
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
