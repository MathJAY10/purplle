from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from app.core.container import AppContainer
from app.core.config import get_settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health_endpoint_reports_system_status(session_maker, fake_redis) -> None:
    app = create_app()
    app.state.container = AppContainer(
        settings=get_settings(),
        engine=None,  # type: ignore[arg-type]
        session_maker=session_maker,
        redis=fake_redis,
        event_publisher=None,  # type: ignore[arg-type]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert "database" in body
    assert "redis" in body
    assert "stale_feed" in body
