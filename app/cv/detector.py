from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.domain.models.inference import BoundingBox, Detection

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DetectorService:
    weights_path: str = "yolov8n.pt"
    confidence_threshold: float = 0.35
    device: str | None = None
    _model: Any = field(default=None, init=False, repr=False)

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is required for YOLOv8 detection"
            ) from exc

        self._model = YOLO(self.weights_path)
        return self._model

    async def detect(self, frame: Any) -> list[Detection]:
        model = self._load_model()

        result = model.predict(
            frame,
            conf=self.confidence_threshold,
            classes=[0],
            verbose=False,
            device=self.device,
        )[0]

        detections: list[Detection] = []

        names = getattr(result, "names", {})
        boxes = getattr(result, "boxes", None)

        if boxes is None:
            print("DETECTIONS FOUND = 0")
            return detections

        for box in boxes:
            confidence = float(
                box.conf.item()
                if hasattr(box.conf, "item")
                else box.conf
            )

            if confidence < self.confidence_threshold:
                continue

            class_id = int(
                box.cls.item()
                if hasattr(box.cls, "item")
                else box.cls
            )

            label = names.get(class_id, "person")

            if label != "person" and class_id != 0:
                continue

            x1, y1, x2, y2 = (
                float(v)
                for v in box.xyxy[0].tolist()
            )

            detections.append(
                Detection(
                    class_id=class_id,
                    label=label,
                    confidence=confidence,
                    bbox=BoundingBox(
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                    ),
                    metadata={"source": "yolov8n"},
                )
            )

        logger.debug(
            "detector_frame_processed",
            extra={"detected_count": len(detections)},
        )

        print(f"DETECTIONS FOUND = {len(detections)}")

        return detections