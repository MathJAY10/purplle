from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import math


@dataclass(frozen=True, slots=True)
class Point2D:
    """2D point representation for trajectory and spatial calculations."""

    x: float
    y: float

    def distance_to(self, other: Point2D) -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True, slots=True)
class Detection:
    class_id: int
    label: str
    confidence: float
    bbox: BoundingBox
    is_staff: bool = False  # Staff detection flag
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrackedObject:
    track_id: int
    detection: Detection
    visitor_id: str | None = None  # Re-ID token - unique per visit session
    frame_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
