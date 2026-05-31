from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.container import build_container
from app.core.logging import configure_logging
from app.infrastructure.redis.consumer import RedisStreamConsumer
from app.services.event_processor_service import RetailEventProcessorService
from app.infrastructure.repositories.events import SQLAlchemyEventRepository
from app.infrastructure.repositories.sessions import SQLAlchemySessionRepository
from app.workers.event_worker import EventStreamWorker


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    container = build_container(settings)
    consumer = RedisStreamConsumer(
        redis=container.redis,
        stream_name=settings.redis_stream_name,
        group_name=settings.redis_consumer_group,
        consumer_name=settings.redis_consumer_name,
    )
    processor = RetailEventProcessorService(
        session_maker=container.session_maker,
        event_repository=SQLAlchemyEventRepository(container.session_maker),
        session_repository=SQLAlchemySessionRepository(container.session_maker),
    )
    worker = EventStreamWorker(consumer=consumer, processor=processor)
    try:
        await worker.run()
    finally:
        await container.aclose()


if __name__ == "__main__":
    asyncio.run(main())