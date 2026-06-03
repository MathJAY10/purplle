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

    async def get_funnel_data(self, store_id: str, start_time: datetime, end_time: datetime) -> dict:
        async with self._session_maker() as session:
            # 1. Entry count
            stmt_entry = select(func.count(SessionRecord.session_id)).where(
                SessionRecord.store_id == store_id,
                SessionRecord.is_staff == False,
                SessionRecord.opened_at >= start_time,
                SessionRecord.opened_at <= end_time,
            )
            entry_count = await session.scalar(stmt_entry) or 0
            
            # 2. Zone visit count
            stmt_zone = (
                select(func.count(SessionRecord.session_id.distinct()))
                .select_from(EventRecord)
                .join(SessionRecord, EventRecord.session_id == SessionRecord.session_id)
                .where(
                    SessionRecord.store_id == store_id,
                    SessionRecord.is_staff == False,
                    SessionRecord.opened_at >= start_time,
                    SessionRecord.opened_at <= end_time,
                    EventRecord.event_type == "ZONE_ENTER"
                )
            )
            zone_visit_count = await session.scalar(stmt_zone) or 0
            
            # 3. Billing events (session_id, earliest billing_time)
            stmt_billing = (
                select(EventRecord.session_id, func.min(EventRecord.occurred_at))
                .select_from(EventRecord)
                .join(SessionRecord, EventRecord.session_id == SessionRecord.session_id)
                .where(
                    SessionRecord.store_id == store_id,
                    SessionRecord.is_staff == False,
                    SessionRecord.opened_at >= start_time,
                    SessionRecord.opened_at <= end_time,
                    EventRecord.event_type == "ZONE_ENTER",
                    EventRecord.zone_id == "billing"
                )
                .group_by(EventRecord.session_id)
                .order_by(func.min(EventRecord.occurred_at))
            )
            billing_result = await session.execute(stmt_billing)
            billing_sessions = [
                {"session_id": row[0], "billing_time": row[1]} 
                for row in billing_result.all()
            ]
            
            # 4. Transactions
            from app.db.models.transaction import TransactionRecord
            stmt_txn = (
                select(TransactionRecord.transaction_id, TransactionRecord.timestamp)
                .where(
                    TransactionRecord.store_id == store_id,
                    TransactionRecord.timestamp >= start_time,
                    TransactionRecord.timestamp <= end_time
                )
                .order_by(TransactionRecord.timestamp)
            )
            txn_result = await session.execute(stmt_txn)
            transactions = [
                {"transaction_id": row[0], "timestamp": row[1]}
                for row in txn_result.all()
            ]
            
            return {
                "entry_count": int(entry_count),
                "zone_visit_count": int(zone_visit_count),
                "billing_sessions": billing_sessions,
                "transactions": transactions
            }

    async def get_queue_ledger_data(self, store_id: str, start_time: datetime, end_time: datetime) -> dict:
        async with self._session_maker() as session:
            # 1. Baseline: sessions in billing queue strictly before start_time
            # Get the latest event before start_time for each session in billing zone
            subq = (
                select(
                    EventRecord.session_id,
                    func.max(EventRecord.occurred_at).label("last_event_time")
                )
                .join(SessionRecord, EventRecord.session_id == SessionRecord.session_id)
                .where(
                    SessionRecord.store_id == store_id,
                    SessionRecord.is_staff == False,
                    EventRecord.zone_id == "billing",
                    EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_EXIT"]),
                    EventRecord.occurred_at < start_time
                )
                .group_by(EventRecord.session_id)
                .subquery()
            )
            
            baseline_stmt = (
                select(EventRecord.session_id)
                .join(subq, (EventRecord.session_id == subq.c.session_id) & (EventRecord.occurred_at == subq.c.last_event_time))
                .where(EventRecord.event_type == "ZONE_ENTER")
            )
            
            baseline_result = await session.execute(baseline_stmt)
            baseline_sessions = [row[0] for row in baseline_result.all()]
            
            # 2. Ledger: all ENTER/EXIT events in the window
            ledger_stmt = (
                select(EventRecord.session_id, EventRecord.event_type, EventRecord.occurred_at)
                .join(SessionRecord, EventRecord.session_id == SessionRecord.session_id)
                .where(
                    SessionRecord.store_id == store_id,
                    SessionRecord.is_staff == False,
                    EventRecord.zone_id == "billing",
                    EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_EXIT"]),
                    EventRecord.occurred_at >= start_time,
                    EventRecord.occurred_at <= end_time
                )
                .order_by(EventRecord.occurred_at.asc())
            )
            ledger_result = await session.execute(ledger_stmt)
            ledger_events = [
                {"session_id": row[0], "event_type": row[1], "occurred_at": row[2]}
                for row in ledger_result.all()
            ]
            
            return {
                "baseline_sessions": baseline_sessions,
                "ledger_events": ledger_events
            }
