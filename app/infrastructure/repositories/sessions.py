from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.session import SessionRecord


class SQLAlchemySessionRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def get_active_by_store_and_track(self, session: AsyncSession, store_id: str, track_id: str) -> SessionRecord | None:
        statement = (
            select(SessionRecord)
            .where(SessionRecord.store_id == store_id)
            .where(SessionRecord.track_id == track_id)
            .where(SessionRecord.status == "active")
            .order_by(SessionRecord.opened_at.desc())
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_active_by_store_and_visitor(self, session: AsyncSession, store_id: str, visitor_id: str) -> SessionRecord | None:
        statement = (
            select(SessionRecord)
            .where(SessionRecord.store_id == store_id)
            .where(SessionRecord.visitor_id == visitor_id)
            .where(SessionRecord.status == "active")
            .order_by(SessionRecord.opened_at.desc())
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def create_active_session(
        self,
        session: AsyncSession,
        store_id: str,
        track_id: str,
        entry_event_id: UUID,
        opened_at: datetime,
        visitor_id: str | None = None,
        is_staff: bool = False,
    ) -> SessionRecord:
        record = SessionRecord(
            session_id=uuid4(),
            store_id=store_id,
            track_id=track_id,
            entry_event_id=entry_event_id,
            exit_event_id=None,
            opened_at=opened_at,
            closed_at=None,
            duration_ms=None,
            status="active",
            visitor_id=visitor_id,
            is_staff=is_staff,
        )
        session.add(record)
        return record

    async def close_session(self, session: AsyncSession, session_id: UUID, exit_event_id: UUID, closed_at: datetime) -> SessionRecord | None:
        record = await session.get(SessionRecord, session_id)
        if record is None:
            return None
        if record.status != "active":
            return record
        record.exit_event_id = exit_event_id
        record.closed_at = closed_at
        opened_at = self._ensure_aware(record.opened_at)
        closed_at = self._ensure_aware(closed_at)
        record.duration_ms = max(0, int((closed_at - opened_at).total_seconds() * 1000))
        record.status = "closed"
        return record

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
