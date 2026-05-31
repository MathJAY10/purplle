from __future__ import annotations

import logging
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RedisStreamConsumer:
    redis: Redis
    stream_name: str
    group_name: str
    consumer_name: str
    block_ms: int = 1000
    count: int = 10

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(name=self.stream_name, groupname=self.group_name, id="0", mkstream=True)
        except Exception as exc:  # noqa: BLE001
            if "BUSYGROUP" not in str(exc):
                raise

    async def claim_pending(self, idle_ms: int = 30000, count: int = 10):
        try:
            next_start, messages, _deleted = await self.redis.xautoclaim(
                name=self.stream_name,
                groupname=self.group_name,
                consumername=self.consumer_name,
                min_idle_time=idle_ms,
                start_id="0-0",
                count=count,
            )
            return [(self.stream_name, messages)] if messages else []
        except AttributeError:
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "redis_claim_retry",
                extra={
                    "stream_name": self.stream_name,
                    "group_name": self.group_name,
                    "consumer_name": self.consumer_name,
                    "idle_ms": idle_ms,
                },
            )
            raise exc

    async def read(self):
        return await self.redis.xreadgroup(
            groupname=self.group_name,
            consumername=self.consumer_name,
            streams={self.stream_name: ">"},
            count=self.count,
            block=self.block_ms,
        )

    async def ack(self, message_id: str) -> int:
        return await self.redis.xack(self.stream_name, self.group_name, message_id)
