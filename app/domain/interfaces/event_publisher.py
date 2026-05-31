from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models.inference import PipelineEvent


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, stream_name: str, event: PipelineEvent) -> str:
        raise NotImplementedError
