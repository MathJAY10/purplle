from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert

from app.db.models.transaction import TransactionRecord

class SQLAlchemyTransactionRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def bulk_insert(self, session: AsyncSession, records: list[dict]) -> None:
        if not records:
            return
            
        # Use ON CONFLICT DO NOTHING to ensure idempotent ingestion
        stmt = insert(TransactionRecord).values(records).on_conflict_do_nothing(
            index_elements=['transaction_id']
        )
        await session.execute(stmt)
