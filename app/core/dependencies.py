from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.domain.container import AppContainer
from app.infrastructure.repositories.events import SQLAlchemyEventRepository
from app.infrastructure.repositories.sessions import SQLAlchemySessionRepository
from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.services.event_ingest_service import RetailEventIngestService
from app.services.event_processor_service import RetailEventProcessorService


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_app_settings() -> Settings:
    return get_settings()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.container.session_maker() as session:
        yield session


def get_redis_client(request: Request) -> Redis:
    return request.app.state.container.redis


def get_event_ingest_service(request: Request) -> RetailEventIngestService:
    container = request.app.state.container
    return RetailEventIngestService(event_publisher=container.event_publisher)


def get_event_processor_service(request: Request) -> RetailEventProcessorService:
    container = request.app.state.container
    event_repository = SQLAlchemyEventRepository(session_maker=container.session_maker)
    session_repository = SQLAlchemySessionRepository(session_maker=container.session_maker)
    return RetailEventProcessorService(
        session_maker=container.session_maker,
        event_repository=event_repository,
        session_repository=session_repository,
    )


def get_analytics_repository(request: Request) -> AnalyticsRepository:
    container = request.app.state.container
    return AnalyticsRepository(container.session_maker)
