from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class VideoFrame:
    frame_number: int
    image: Any


@dataclass(frozen=True, slots=True)
class DetectedBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    label: str


@dataclass(frozen=True, slots=True)
class TrackedBox(DetectedBox):
    track_id: int
