from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
import logging


class BaseWorker(ABC):
    def __init__(self, name: str, logger: logging.Logger | None = None) -> None:
        self.name = name
        self._logger = logger or logging.getLogger(name)
        self._stop_event = asyncio.Event()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def stop(self) -> None:
        self._stop_event.set()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    async def run(self) -> None:
        self.logger.info("worker_starting", extra={"worker": self.name})
        try:
            await self.execute()
        except asyncio.CancelledError:
            self.logger.info("worker_cancelled", extra={"worker": self.name})
            raise
        except Exception:
            self.logger.exception("worker_failed", extra={"worker": self.name})
            raise
        finally:
            self.logger.info("worker_stopped", extra={"worker": self.name})

    @abstractmethod
    async def execute(self) -> None:
        raise NotImplementedError
