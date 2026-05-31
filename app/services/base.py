from __future__ import annotations

from abc import ABC
import logging


class BaseService(ABC):
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    @property
    def logger(self) -> logging.Logger:
        return self._logger
