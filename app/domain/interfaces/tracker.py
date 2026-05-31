from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.domain.models.inference import Detection, TrackedObject


class Tracker(ABC):
    @abstractmethod
    async def track(self, detections: Sequence[Detection], frame_index: int | None = None) -> Sequence[TrackedObject]:
        raise NotImplementedError
