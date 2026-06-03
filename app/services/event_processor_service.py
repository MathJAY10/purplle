from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.events import EventType, RetailEvent
from app.infrastructure.repositories.events import SQLAlchemyEventRepository
from app.infrastructure.repositories.sessions import SQLAlchemySessionRepository


class RetailEventProcessorService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        event_repository: SQLAlchemyEventRepository,
        session_repository: SQLAlchemySessionRepository,
    ) -> None:
        self._session_maker = session_maker
        self._event_repository = event_repository
        self._session_repository = session_repository

    async def process(self, event: RetailEvent) -> bool:
        async with self._session_maker() as session:
            async with session.begin():
                if event.idempotency_key and await self._event_repository.exists(session, event.idempotency_key):
                    return False

                # Look up the active session of this visitor or track
                active_session = None
                if event.visitor_id:
                    active_session = await self._session_repository.get_active_by_store_and_visitor(session, event.store_id, event.visitor_id)
                elif event.track_id:
                    active_session = await self._session_repository.get_active_by_store_and_track(session, event.store_id, event.track_id)

                session_id = active_session.session_id if active_session else None
                event_to_add = event
                if session_id and not event.session_id:
                    event_to_add = event.model_copy(update={"session_id": session_id})

                stored_event = await self._event_repository.add(session, event_to_add)
                try:
                    await session.flush()
                except IntegrityError:
                    await session.rollback()
                    return False

                is_entry = stored_event.event_type in (EventType.ENTRY.value, EventType.REENTRY.value)
                is_exit = stored_event.event_type == EventType.EXIT.value

                if is_entry and active_session is None:
                    created_session = await self._session_repository.create_active_session(
                        session=session,
                        store_id=event.store_id,
                        track_id=event.track_id or "unknown",
                        entry_event_id=stored_event.event_id,
                        opened_at=stored_event.occurred_at,
                        visitor_id=event.visitor_id,
                        is_staff=event.is_staff,
                    )
                    stored_event.session_id = created_session.session_id
                elif is_exit and active_session is not None:
                    await self._session_repository.close_session(
                        session=session,
                        session_id=active_session.session_id,
                        exit_event_id=stored_event.event_id,
                        closed_at=stored_event.occurred_at,
                    )
                return True
