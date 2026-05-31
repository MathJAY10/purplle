from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.infrastructure.redis.publisher import RedisStreamEventPublisher
from app.redis.client import create_redis_client


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]
    redis: Redis
    event_publisher: RedisStreamEventPublisher

    async def aclose(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()


def build_container(settings: Settings) -> AppContainer:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
        pool_pre_ping=True,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    redis = create_redis_client(settings)
    event_publisher = RedisStreamEventPublisher(redis=redis, stream_name=settings.redis_stream_name)
    return AppContainer(
        settings=settings,
        engine=engine,
        session_maker=session_maker,
        redis=redis,
        event_publisher=event_publisher,
    )
