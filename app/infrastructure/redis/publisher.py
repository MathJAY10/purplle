from __future__ import annotations

import logging
from asyncio import sleep
from dataclasses import dataclass

from redis.asyncio import Redis

from app.domain.events import RetailEvent

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RedisStreamEventPublisher:
    redis: Redis
    stream_name: str
    max_retries: int = 3
    retry_delay_seconds: float = 0.25

    async def ensure_consumer_group(self, group_name: str) -> None:
        try:
            await self.redis.xgroup_create(name=self.stream_name, groupname=group_name, id="0", mkstream=True)
        except Exception as exc:  # noqa: BLE001
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish(self, event: RetailEvent) -> str:
        event_data = {
            "event_id": str(event.event_id),
            "idempotency_key": event.idempotency_key or str(event.event_id),
            "store_id": event.store_id,
            "camera_id": event.camera_id,
            "event_type": event.event_type.value,
            "occurred_at": event.occurred_at.isoformat(),
            "track_id": event.track_id or "",
            "session_id": str(event.session_id) if event.session_id else "",
            "payload": event.model_dump_json(),
            "trace_id": event.trace_id or "",
        }
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self.redis.xadd(self.stream_name, event_data)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "redis_publish_retry",
                    extra={
                        "trace_id": event.trace_id,
                        "event_id": str(event.event_id),
                        "store_id": event.store_id,
                        "attempt": attempt,
                    },
                )
                if attempt < self.max_retries:
                    await sleep(self.retry_delay_seconds * attempt)

        logger.error(
            "redis_publish_failed",
            extra={
                "trace_id": event.trace_id,
                "event_id": str(event.event_id),
                "store_id": event.store_id,
                "error": str(last_error) if last_error is not None else "unknown",
            },
        )
        raise last_error if last_error is not None else RuntimeError("Redis publish failed")
