from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

TEntity = TypeVar("TEntity")


class Repository(ABC, Generic[TEntity]):
    @abstractmethod
    async def get_by_id(self, identifier: Any) -> TEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, entity: TEntity) -> TEntity:
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity: TEntity) -> TEntity:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, identifier: Any) -> None:
        raise NotImplementedError
