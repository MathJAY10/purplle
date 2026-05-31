from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.inference import TrackedObject
from app.cv.crossing import LineCrossingConfig


@dataclass(slots=True)
class DebugVisualizer:
    def draw(self, frame, tracked_objects: list[TrackedObject], config: LineCrossingConfig):
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("opencv-python-headless is required for debug visualization") from exc

        annotated = frame.copy()
        cv2.line(annotated, (int(config.x1), int(config.y1)), (int(config.x2), int(config.y2)), (0, 255, 255), 2)
        for tracked_object in tracked_objects:
            bbox = tracked_object.detection.bbox
            cv2.rectangle(annotated, (int(bbox.x1), int(bbox.y1)), (int(bbox.x2), int(bbox.y2)), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"ID {tracked_object.track_id}",
                (int(bbox.x1), max(0, int(bbox.y1) - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )
        return annotated
