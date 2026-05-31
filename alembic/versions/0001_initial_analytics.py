from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_analytics"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("event_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("store_id", sa.String(length=128), nullable=False),
        sa.Column("camera_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("track_id", sa.String(length=128), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("event_id", name="uq_events_event_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_events_idempotency_key"),
    )
    op.create_index("ix_events_store_id", "events", ["store_id"])
    op.create_index("ix_events_occurred_at", "events", ["occurred_at"])
    op.create_index("ix_events_event_type", "events", ["event_type"])

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("store_id", sa.String(length=128), nullable=False),
        sa.Column("track_id", sa.String(length=128), nullable=False),
        sa.Column("entry_event_id", sa.Uuid(), nullable=False),
        sa.Column("exit_event_id", sa.Uuid(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_sessions_store_id", "sessions", ["store_id"])
    op.create_index("ix_sessions_opened_at", "sessions", ["opened_at"])

    op.create_table(
        "anomalies",
        sa.Column("anomaly_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("store_id", sa.String(length=128), nullable=False),
        sa.Column("anomaly_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_anomalies_store_id", "anomalies", ["store_id"])
    op.create_index("ix_anomalies_observed_at", "anomalies", ["observed_at"])
    op.create_index("ix_anomalies_anomaly_type", "anomalies", ["anomaly_type"])

    op.create_table(
        "metrics_cache",
        sa.Column("cache_id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("store_id", sa.String(length=128), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.JSON(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("store_id", "metric_key", name="uq_metrics_cache_store_metric"),
    )
    op.create_index("ix_metrics_cache_store_id", "metrics_cache", ["store_id"])


def downgrade() -> None:
    op.drop_index("ix_metrics_cache_store_id", table_name="metrics_cache")
    op.drop_table("metrics_cache")

    op.drop_index("ix_anomalies_anomaly_type", table_name="anomalies")
    op.drop_index("ix_anomalies_observed_at", table_name="anomalies")
    op.drop_index("ix_anomalies_store_id", table_name="anomalies")
    op.drop_table("anomalies")

    op.drop_index("ix_sessions_opened_at", table_name="sessions")
    op.drop_index("ix_sessions_store_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_occurred_at", table_name="events")
    op.drop_index("ix_events_store_id", table_name="events")
    op.drop_table("events")