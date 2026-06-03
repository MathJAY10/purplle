from datetime import datetime
from collections.abc import Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.db.models.anomaly import AnomalyRecord

class AnomalyRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self._session_maker = session_maker

    async def save_anomalies(self, anomalies: list[AnomalyRecord]) -> None:
        if not anomalies:
            return
            
        async with self._session_maker() as session:
            session.add_all(anomalies)
            await session.commit()

    async def get_anomalies(self, store_id: str, start_time: datetime, end_time: datetime) -> Sequence[AnomalyRecord]:
        async with self._session_maker() as session:
            stmt = select(AnomalyRecord).where(
                AnomalyRecord.store_id == store_id,
                AnomalyRecord.observed_at >= start_time,
                AnomalyRecord.observed_at <= end_time
            ).order_by(AnomalyRecord.observed_at.desc())
            
            result = await session.execute(stmt)
            return result.scalars().all()

    async def check_anomaly_exists(
        self, 
        store_id: str, 
        anomaly_type: str, 
        observed_at: datetime
    ) -> bool:
        """Check if an anomaly was already recorded for this exact observed_at time"""
        async with self._session_maker() as session:
            stmt = select(AnomalyRecord.anomaly_id).where(
                AnomalyRecord.store_id == store_id,
                AnomalyRecord.anomaly_type == anomaly_type,
                AnomalyRecord.observed_at == observed_at
            ).limit(1)
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
