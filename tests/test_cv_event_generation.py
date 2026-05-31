from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.cv.crossing import LineCrossingConfig, LineCrossingEventGenerator
from app.domain.events import EventType, RetailEvent
from app.domain.models.inference import BoundingBox, Detection, TrackedObject


def _tracked(track_id: int, y_center: float) -> TrackedObject:
    detection = Detection(
        class_id=0,
        label="person",
        confidence=0.88,
        bbox=BoundingBox(x1=10, y1=y_center - 10, x2=30, y2=y_center + 10),
        metadata={},
    )
    return TrackedObject(track_id=track_id, detection=detection, frame_index=0, metadata={})


def test_generator_builds_retail_event_payload() -> None:
    generator = LineCrossingEventGenerator(LineCrossingConfig(x1=0, y1=10, x2=100, y2=10, debounce_frames=5, track_ttl_frames=20))
    generator.update(store_id="store-1", camera_id="camera-entry", tracked_object=_tracked(1, 0), frame_number=1)
    events = generator.update(store_id="store-1", camera_id="camera-entry", tracked_object=_tracked(1, 25), frame_number=2)

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, RetailEvent)
    assert event.event_type == EventType.ENTRY
    assert event.store_id == "store-1"
    assert event.camera_id == "camera-entry"
    assert event.payload["frame_number"] == 2
    assert event.payload["direction"] == "in"
