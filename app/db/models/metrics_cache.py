from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MetricsCacheRecord(Base):
    __tablename__ = "metrics_cache"
    __table_args__ = (
        UniqueConstraint("store_id", "metric_key", name="uq_metrics_cache_store_metric"),
        Index("ix_metrics_cache_store_id", "store_id"),
    )

    cache_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
