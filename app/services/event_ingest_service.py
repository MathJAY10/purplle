from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
import logging
from time import perf_counter
from uuid import UUID

from app.domain.events import RetailEvent
from app.infrastructure.redis.publisher import RedisStreamEventPublisher
from app.schemas.events import RetailEventIngestItem


class RetailEventIngestService:
    def __init__(self, event_publisher: RedisStreamEventPublisher) -> None:
        self._event_publisher = event_publisher
        self._logger = logging.getLogger(self.__class__.__name__)

    async def ingest(self, events: Sequence[RetailEventIngestItem], trace_id: str | None = None) -> tuple[list[UUID], list[UUID]]:
        published_event_ids: list[UUID] = []
        duplicate_event_ids: list[UUID] = []

        for item in events:
            started_at = perf_counter()
            idempotency_key = self._build_idempotency_key(item)
            event = RetailEvent.model_validate(
                {
                    **item.model_dump(),
                    "idempotency_key": idempotency_key,
                    "trace_id": trace_id,
                }
            )
            message_id = await self._event_publisher.publish(event)
            if message_id:
                published_event_ids.append(event.event_id)
            else:
                duplicate_event_ids.append(event.event_id)

            latency_ms = round((perf_counter() - started_at) * 1000, 2)
            self._logger.info(
                "event_published",
                extra={
                    "trace_id": trace_id,
                    "event_id": str(event.event_id),
                    "store_id": event.store_id,
                    "latency_ms": latency_ms,
                },
            )

        return published_event_ids, duplicate_event_ids

    def _build_idempotency_key(self, item: RetailEventIngestItem) -> str:
        payload = {
            "store_id": item.store_id,
            "camera_id": item.camera_id,
            "event_type": item.event_type.value,
            "occurred_at": item.occurred_at.isoformat(),
            "track_id": item.track_id,
            "session_id": str(item.session_id) if item.session_id else None,
            "payload": item.payload,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
