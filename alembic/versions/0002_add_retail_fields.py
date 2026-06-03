from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_retail_fields"
down_revision = "0001_initial_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to events
    op.add_column("events", sa.Column("visitor_id", sa.String(length=128), nullable=True))
    op.add_column("events", sa.Column("zone_id", sa.String(length=128), nullable=True))
    op.add_column("events", sa.Column("dwell_ms", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("events", sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("1.0")))
    op.add_column("events", sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    # Add columns to sessions
    op.add_column("sessions", sa.Column("visitor_id", sa.String(length=128), nullable=True))
    op.add_column("sessions", sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # Create indices
    op.create_index("ix_events_visitor_id", "events", ["visitor_id"])
    op.create_index("ix_sessions_visitor_id", "sessions", ["visitor_id"])


def downgrade() -> None:
    # Drop indices
    op.drop_index("ix_sessions_visitor_id", table_name="sessions")
    op.drop_index("ix_events_visitor_id", table_name="events")

    # Drop columns from sessions
    op.drop_column("sessions", "is_staff")
    op.drop_column("sessions", "visitor_id")

    # Drop columns from events
    op.drop_column("events", "metadata_json")
    op.drop_column("events", "confidence")
    op.drop_column("events", "is_staff")
    op.drop_column("events", "dwell_ms")
    op.drop_column("events", "zone_id")
    op.drop_column("events", "visitor_id")
