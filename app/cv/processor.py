from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

from app.cv.crossing import LineCrossingConfig, LineCrossingEventGenerator
from app.cv.detector import DetectorService
from app.cv.tracker import TrackerService
from app.cv.video import VideoStreamReader
from app.cv.visualization import DebugVisualizer
from app.infrastructure.redis.publisher import RedisStreamEventPublisher

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FrameProcessor:
    detector: DetectorService
    tracker: TrackerService
    event_generator: LineCrossingEventGenerator
    publisher: RedisStreamEventPublisher
    store_id: str
    camera_id: str
    debug_visualization: bool = False
    visualizer: DebugVisualizer | None = None

    async def process_video(self, reader: VideoStreamReader) -> int:
        total_events = 0
        for frame in reader.iter_frames():
            started_at = perf_counter()
            detections = await self.detector.detect(frame.image)
            tracked_objects = await self.tracker.track(detections, frame_number=frame.frame_number)

            for tracked_object in tracked_objects:
                events = self.event_generator.update(
                    store_id=self.store_id,
                    camera_id=self.camera_id,
                    tracked_object=tracked_object,
                    frame_number=frame.frame_number,
                )
                for event in events:
                    await self.publisher.publish(event)
                    total_events += 1
                    logger.info(
                        "cv_event_generated",
                        extra={
                            "track_id": tracked_object.track_id,
                            "camera_id": self.camera_id,
                            "event_type": event.event_type.value,
                            "confidence": tracked_object.detection.confidence,
                            "frame_number": frame.frame_number,
                        },
                    )

            self.event_generator.prune(frame.frame_number)

            if self.debug_visualization and self.visualizer is not None:
                self.visualizer.draw(frame.image, tracked_objects, self.event_generator.config)

            latency_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.info(
                "cv_frame_processed",
                extra={
                    "track_id": tracked_objects[0].track_id if tracked_objects else None,
                    "camera_id": self.camera_id,
                    "event_type": None,
                    "confidence": tracked_objects[0].detection.confidence if tracked_objects else None,
                    "frame_number": frame.frame_number,
                    "latency_ms": latency_ms,
                },
            )

        return total_events
