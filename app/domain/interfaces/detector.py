from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.domain.models.inference import Detection


class Detector(ABC):
    @abstractmethod
    async def detect(self, frame: object) -> Sequence[Detection]:
        raise NotImplementedError
