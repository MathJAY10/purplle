from __future__ import annotations

from app.domain.events import RetailEvent
from app.infrastructure.redis.consumer import RedisStreamConsumer
from app.services.event_processor_service import RetailEventProcessorService
from app.workers.base import BaseWorker


class EventStreamWorker(BaseWorker):
    def __init__(self, consumer: RedisStreamConsumer, processor: RetailEventProcessorService) -> None:
        super().__init__(name="event-stream-worker")
        self._consumer = consumer
        self._processor = processor

    async def execute(self) -> None:
        await self._consumer.ensure_group()
        while not self.should_stop():
            batches = await self._consumer.read()
            if not batches:
                pending = await self._consumer.claim_pending()
                if not pending:
                    continue
                batches = pending

            for _, messages in batches:
                for message_id, payload in messages:
                    event = RetailEvent.model_validate_json(payload["payload"])
                    try:
                        await self._processor.process(event)
                        await self._consumer.ack(message_id)
                    except Exception:
                        self.logger.exception(
                            "worker_event_processing_failed",
                            extra={
                                "trace_id": event.trace_id,
                                "event_id": str(event.event_id),
                                "store_id": event.store_id,
                                "camera_id": event.camera_id,
                                "event_type": event.event_type.value,
                            },
                        )
                        raise
