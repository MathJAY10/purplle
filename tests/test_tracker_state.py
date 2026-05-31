from __future__ import annotations

import pytest

from app.cv.tracker import TrackerService
from app.domain.models.inference import BoundingBox, Detection


class FakeByteTrack:
    def __init__(self) -> None:
        self.calls = 0

    def update_with_detections(self, detections):
        self.calls += 1

        class Tracked:
            tracker_id = [42]

        return Tracked()


@pytest.mark.asyncio
async def test_tracker_service_keeps_backend_state() -> None:
    service = TrackerService(frame_rate=30)
    service._tracker = FakeByteTrack()  # test double for stateful tracker backend

    detections = [
        Detection(
            class_id=0,
            label="person",
            confidence=0.9,
            bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10),
            metadata={},
        )
    ]

    first = await service.track(detections, frame_number=1)
    second = await service.track(detections, frame_number=2)

    assert first[0].track_id == 42
    assert second[0].track_id == 42
    assert service._tracker.calls == 2
