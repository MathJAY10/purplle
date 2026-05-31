from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.models.inference import BoundingBox, Detection, TrackedObject


@dataclass(slots=True)
class TrackerService:
    frame_rate: int = 30
    _tracker: Any = field(default=None, init=False, repr=False)

    def _load_tracker(self):
        if self._tracker is not None:
            return self._tracker

        try:
            import supervision as sv
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("supervision is required for ByteTrack integration") from exc

        self._tracker = sv.ByteTrack(frame_rate=self.frame_rate)
        return self._tracker

    def _is_custom_backend(self, backend: Any) -> bool:
        return not getattr(backend.__class__, "__module__", "").startswith("supervision")

    async def track(self, detections: list[Detection], frame_number: int | None = None) -> list[TrackedObject]:
        tracker = self._load_tracker()
        if not detections:
            return []

        if self._tracker is not None and self._is_custom_backend(tracker):
            tracked = tracker.update_with_detections(detections)
            tracker_ids = getattr(tracked, "tracker_id", []) or []
            results: list[TrackedObject] = []
            for index, detection in enumerate(detections):
                track_id = tracker_ids[index] if len(tracker_ids) > index else index + 1
                results.append(
                    TrackedObject(
                        track_id=int(track_id),
                        detection=detection,
                        frame_index=frame_number,
                        metadata={"backend": "custom"},
                    )
                )
            return results

        try:
            import supervision as sv
            import numpy as np
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("supervision and numpy are required for tracking") from exc

        xyxy = np.array([[d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2] for d in detections], dtype=float)
        confidence = np.array([d.confidence for d in detections], dtype=float)
        class_id = np.array([d.class_id for d in detections], dtype=int)
        sv_detections = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
        tracked = tracker.update_with_detections(sv_detections)

        results: list[TrackedObject] = []
        for index, detection in enumerate(detections):
            track_id = None
            if getattr(tracked, "tracker_id", None) is not None and len(tracked.tracker_id) > index:
                track_id = tracked.tracker_id[index]
            if track_id is None:
                track_id = index + 1
            results.append(
                TrackedObject(
                    track_id=int(track_id),
                    detection=detection,
                    frame_index=frame_number,
                    metadata={"backend": "bytetrack"},
                )
            )
        return results
