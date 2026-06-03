from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, JSON, String, UniqueConstraint, Uuid, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventRecord(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_events_event_id"),
        UniqueConstraint("idempotency_key", name="uq_events_idempotency_key"),
        Index("ix_events_store_id", "store_id"),
        Index("ix_events_occurred_at", "occurred_at"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_visitor_id", "visitor_id"),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    store_id: Mapped[str] = mapped_column(String(128), nullable=False)
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    track_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    visitor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dwell_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

