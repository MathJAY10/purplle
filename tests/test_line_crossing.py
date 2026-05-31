from __future__ import annotations

from app.cv.crossing import LineCrossingConfig, LineCrossingEventGenerator
from app.domain.events import EventType
from app.domain.models.inference import BoundingBox, Detection, TrackedObject


def _tracked(track_id: int, x1: float, y1: float, x2: float, y2: float, confidence: float = 0.9) -> TrackedObject:
    detection = Detection(
        class_id=0,
        label="person",
        confidence=confidence,
        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
        metadata={},
    )
    return TrackedObject(track_id=track_id, detection=detection, frame_index=0, metadata={})


def test_entry_event_emits_on_crossing() -> None:
    generator = LineCrossingEventGenerator(LineCrossingConfig(x1=0, y1=10, x2=100, y2=10, debounce_frames=5, track_ttl_frames=20))

    first = generator.update(store_id="store-1", camera_id="camera-1", tracked_object=_tracked(1, 10, 0, 20, 10), frame_number=1)
    second = generator.update(store_id="store-1", camera_id="camera-1", tracked_object=_tracked(1, 10, 20, 20, 30), frame_number=2)

    assert first == []
    assert len(second) == 1
    assert second[0].event_type == EventType.ENTRY
    assert second[0].track_id == "1"


def test_exit_event_emits_on_reverse_crossing() -> None:
    generator = LineCrossingEventGenerator(LineCrossingConfig(x1=0, y1=10, x2=100, y2=10, debounce_frames=5, track_ttl_frames=20))

    generator.update(store_id="store-1", camera_id="camera-1", tracked_object=_tracked(2, 10, 20, 20, 30), frame_number=1)
    events = generator.update(store_id="store-1", camera_id="camera-1", tracked_object=_tracked(2, 10, 0, 20, 10), frame_number=2)

    assert len(events) == 1
    assert events[0].event_type == EventType.EXIT


def test_debounce_prevents_duplicate_crossings() -> None:
    generator = LineCrossingEventGenerator(LineCrossingConfig(x1=0, y1=10, x2=100, y2=10, debounce_frames=5, track_ttl_frames=20))

    generator.update(store_id="store-1", camera_id="camera-1", tracked_object=_tracked(3, 10, 0, 20, 10), frame_number=1)
    first_event = generator.update(store_id="store-1", camera_id="camera-1", tracked_object=_tracked(3, 10, 20, 20, 30), frame_number=2)
    duplicate_event = generator.update(store_id="store-1", camera_id="camera-1", tracked_object=_tracked(3, 10, 0, 20, 10), frame_number=3)

    assert len(first_event) == 1
    assert duplicate_event == []
