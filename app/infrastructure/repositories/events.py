from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.event import EventRecord
from app.domain.events import RetailEvent


class SQLAlchemyEventRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def get_by_id(self, session: AsyncSession, event_id: UUID) -> EventRecord | None:
        return await session.get(EventRecord, event_id)

    async def get_by_idempotency_key(self, session: AsyncSession, idempotency_key: str) -> EventRecord | None:
        statement = select(EventRecord).where(EventRecord.idempotency_key == idempotency_key)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def add(self, session: AsyncSession, event: RetailEvent) -> EventRecord:
        record = EventRecord(
            event_id=event.event_id,
            idempotency_key=event.idempotency_key or str(event.event_id),
            store_id=event.store_id,
            camera_id=event.camera_id,
            event_type=event.event_type.value,
            occurred_at=event.occurred_at,
            track_id=event.track_id,
            session_id=event.session_id,
            payload=event.payload,
            trace_id=event.trace_id,
        )
        session.add(record)
        return record

    async def exists(self, session: AsyncSession, idempotency_key: str) -> bool:
        return await self.get_by_idempotency_key(session, idempotency_key) is not None
