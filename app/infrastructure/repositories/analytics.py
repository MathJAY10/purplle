from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.anomaly import AnomalyRecord
from app.db.models.event import EventRecord
from app.db.models.metrics_cache import MetricsCacheRecord
from app.db.models.session import SessionRecord


class AnalyticsRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def last_event_timestamp(self, store_id: str) -> datetime | None:
        async with self._session_maker() as session:
            statement = select(func.max(EventRecord.occurred_at)).where(EventRecord.store_id == store_id)
            result = await session.scalar(statement)
            return result

    async def unique_visitors(self, store_id: str) -> int:
        async with self._session_maker() as session:
            statement = select(func.count(func.distinct(SessionRecord.track_id))).where(SessionRecord.store_id == store_id)
            result = await session.scalar(statement)
            return int(result or 0)

    async def entry_count(self, store_id: str) -> int:
        async with self._session_maker() as session:
            statement = select(func.count()).where(EventRecord.store_id == store_id).where(EventRecord.event_type == "ENTRY")
            result = await session.scalar(statement)
            return int(result or 0)

    async def exit_count(self, store_id: str) -> int:
        async with self._session_maker() as session:
            statement = select(func.count()).where(EventRecord.store_id == store_id).where(EventRecord.event_type == "EXIT")
            result = await session.scalar(statement)
            return int(result or 0)

    async def avg_dwell_ms(self, store_id: str) -> float:
        async with self._session_maker() as session:
            statement = select(func.avg(SessionRecord.duration_ms)).where(SessionRecord.store_id == store_id).where(SessionRecord.duration_ms.is_not(None))
            result = await session.scalar(statement)
            return float(result or 0.0)

    async def queue_depth(self, store_id: str) -> int:
        async with self._session_maker() as session:
            dialect_name = session.bind.dialect.name if session.bind is not None else ""
            if dialect_name == "sqlite":
                zone_expr = func.coalesce(func.json_extract(EventRecord.payload, "$.zone"), "unknown")
            else:
                zone_expr = func.coalesce(EventRecord.payload["zone"].as_string(), "unknown")
            statement = select(func.count()).where(EventRecord.store_id == store_id).where(zone_expr == "billing")
            result = await session.scalar(statement)
            return int(result or 0)

    async def abandonment_rate(self, store_id: str) -> float:
        entries = await self.entry_count(store_id)
        exits = await self.exit_count(store_id)
        if entries == 0:
            return 0.0
        abandoned = max(0, entries - exits)
        return round(abandoned / entries, 4)

    async def zone_metrics(self, store_id: str) -> list[dict[str, object]]:
        async with self._session_maker() as session:
            dialect_name = session.bind.dialect.name if session.bind is not None else ""
            if dialect_name == "sqlite":
                statement = text(
                    """
                    SELECT COALESCE(json_extract(payload, '$.zone'), 'unknown') AS zone,
                           COUNT(*) AS visits,
                           COALESCE(AVG(CAST(json_extract(payload, '$.dwell_ms') AS REAL)), 0) AS avg_dwell_ms
                    FROM events
                    WHERE store_id = :store_id
                    GROUP BY COALESCE(json_extract(payload, '$.zone'), 'unknown')
                    ORDER BY visits DESC
                    """
                )
            else:
                statement = text(
                    """
                    SELECT COALESCE(payload->>'zone', 'unknown') AS zone,
                           COUNT(*) AS visits,
                           COALESCE(AVG((payload->>'dwell_ms')::float), 0) AS avg_dwell_ms
                    FROM events
                    WHERE store_id = :store_id
                    GROUP BY COALESCE(payload->>'zone', 'unknown')
                    ORDER BY visits DESC
                    """
                )
            result = await session.execute(statement, {"store_id": store_id})
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def anomaly_rows(self, store_id: str) -> list[AnomalyRecord]:
        async with self._session_maker() as session:
            statement = select(AnomalyRecord).where(AnomalyRecord.store_id == store_id).order_by(AnomalyRecord.observed_at.desc())
            result = await session.scalars(statement)
            return list(result.all())

    async def upsert_metrics_cache(self, store_id: str, metric_key: str, metric_value: dict[str, object], period_start: datetime | None = None, period_end: datetime | None = None) -> None:
        async with self._session_maker() as session:
            statement = select(MetricsCacheRecord).where(MetricsCacheRecord.store_id == store_id).where(MetricsCacheRecord.metric_key == metric_key)
            existing = await session.scalar(statement)
            if existing is None:
                existing = MetricsCacheRecord(store_id=store_id, metric_key=metric_key, metric_value=metric_value, period_start=period_start, period_end=period_end)
                session.add(existing)
            else:
                existing.metric_value = metric_value
                existing.period_start = period_start
                existing.period_end = period_end
            await session.commit()
