from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.events import EventType, RetailEvent
from app.infrastructure.redis.consumer import RedisStreamConsumer
from app.infrastructure.redis.publisher import RedisStreamEventPublisher


@pytest.mark.asyncio
async def test_redis_publish_and_consume(fake_redis) -> None:
    publisher = RedisStreamEventPublisher(redis=fake_redis, stream_name="events.stream")
    consumer = RedisStreamConsumer(
        redis=fake_redis,
        stream_name="events.stream",
        group_name="worker-group",
        consumer_name="worker-1",
    )

    event = RetailEvent(
        idempotency_key="event-1",
        store_id="store-1",
        camera_id="camera-1",
        event_type=EventType.ENTRY,
        occurred_at=datetime.now(timezone.utc),
        track_id="track-1",
        payload={"zone": "entry"},
    )

    message_id = await publisher.publish(event)
    assert message_id == "1-0"

    await consumer.ensure_group()
    batches = await consumer.read()
    assert batches
    _, messages = batches[0]
    assert messages[0][1]["event_id"] == str(event.event_id)

    acked = await consumer.ack(messages[0][0])
    assert acked == 1
