from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import EventRecord, SessionRecord


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.groups: dict[tuple[str, str], set[str]] = {}

    async def xgroup_create(self, name: str, groupname: str, id: str = "0", mkstream: bool = False) -> None:
        key = (name, groupname)
        if key in self.groups:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        if mkstream:
            self.streams.setdefault(name, [])
        self.groups[key] = set()

    async def xadd(self, stream_name: str, data: dict[str, str]) -> str:
        stream = self.streams.setdefault(stream_name, [])
        message_id = f"{len(stream) + 1}-0"
        stream.append((message_id, data))
        return message_id

    async def xreadgroup(self, groupname: str, consumername: str, streams: dict[str, str], count: int = 10, block: int = 0):
        stream_name = next(iter(streams))
        stream = self.streams.get(stream_name, [])
        pending = self.groups.setdefault((stream_name, groupname), set())
        messages = [(message_id, payload) for message_id, payload in stream if message_id not in pending][:count]
        for message_id, _ in messages:
            pending.add(message_id)
        return [(stream_name, messages)] if messages else []

    async def xack(self, stream_name: str, groupname: str, *message_ids: str) -> int:
        pending = self.groups.setdefault((stream_name, groupname), set())
        acked = 0
        for message_id in message_ids:
            if message_id in pending:
                pending.remove(message_id)
                acked += 1
        return acked

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


@pytest_asyncio.fixture
async def session_maker(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    db_path = tmp_path / "store_intelligence.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()
