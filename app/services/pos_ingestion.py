import csv
import logging
import zoneinfo
from typing import BinaryIO
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.infrastructure.repositories.transactions import SQLAlchemyTransactionRepository

logger = logging.getLogger(__name__)

class POSIngestionService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        repository: SQLAlchemyTransactionRepository
    ) -> None:
        self._session_maker = session_maker
        self._repository = repository

    async def ingest_csv(self, file_stream: BinaryIO, store_timezone: str = "UTC") -> dict:
        """Ingests POS transactions from a CSV file stream."""
        content = file_stream.read().decode("utf-8")
        reader = csv.DictReader(content.splitlines())
        
        try:
            tz = zoneinfo.ZoneInfo(store_timezone)
        except zoneinfo.ZoneInfoNotFoundError:
            logger.warning(f"Invalid timezone {store_timezone}, falling back to UTC")
            tz = timezone.utc
            
        records = []
        parsed = 0
        errors = 0
        
        for row in reader:
            try:
                # Expected format: transaction_id, store_id, timestamp, basket_value_inr
                dt_str = row["timestamp"].replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                
                if dt.tzinfo is None:
                    # Naive datetime: localize using store_timezone
                    dt = dt.replace(tzinfo=tz)
                
                # Convert to UTC for standardized persistence
                dt_utc = dt.astimezone(timezone.utc)
                
                records.append({
                    "transaction_id": row["transaction_id"],
                    "store_id": row["store_id"],
                    "timestamp": dt_utc,
                    "basket_value_inr": Decimal(row["basket_value_inr"])
                })
                parsed += 1
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse CSV row: {row}. Error: {e}")
                errors += 1
                
            if len(records) >= 1000:
                async with self._session_maker() as session:
                    async with session.begin():
                        await self._repository.bulk_insert(session, records)
                records.clear()
                
        if records:
            async with self._session_maker() as session:
                async with session.begin():
                    await self._repository.bulk_insert(session, records)
            
        return {"parsed": parsed, "errors": errors}
