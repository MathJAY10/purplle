from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from time import perf_counter

from app.cv.crossing import LineCrossingEventGenerator
from app.cv.detector import DetectorService
from app.cv.tracker import TrackerService
from app.cv.video import VideoStreamReader
from app.cv.visualization import DebugVisualizer
from app.cv.visitor_reid import VisitorReIDManager, ReIDConfig
from app.cv.staff_detector import StaffDetector, StaffDetectionConfig
from app.cv.zone_tracker import ZoneTracker
from app.domain.events import EventType
from app.domain.models.inference import Point2D
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
    reid_manager: VisitorReIDManager | None = None
    staff_detector: StaffDetector | None = None
    zone_tracker: ZoneTracker | None = None
    zone_polygons: dict[str, dict[str, object]] | None = None

    def __post_init__(self) -> None:
        """Initialize Re-ID, staff detection, and zone tracking if not provided."""
        if self.reid_manager is None:
            self.reid_manager = VisitorReIDManager(ReIDConfig())

        if self.staff_detector is None:
            self.staff_detector = StaffDetector(StaffDetectionConfig())

        if self.zone_tracker is None:
            self.zone_tracker = ZoneTracker(self.store_id, self.camera_id)
            if self.zone_polygons:
                self.zone_tracker.register_zones(self.zone_polygons)

    async def process_video(self, reader: VideoStreamReader) -> int:
        total_events = 0

        print("=== PIPELINE STARTED ===")

        for frame in reader.iter_frames():
            started_at = perf_counter()

            detections = await self.detector.detect(frame.image)

            tracked_objects = await self.tracker.track(
                detections,
                frame_number=frame.frame_number,
            )

            print(
                f"FRAME={frame.frame_number} "
                f"DETECTIONS={len(detections)} "
                f"TRACKED={len(tracked_objects)}"
            )

            # Update Re-ID and get visitor_id for each tracked object
            for tracked_object in tracked_objects:
                # Calculate centroid for Re-ID
                centroid_x = (tracked_object.detection.bbox.x1 + tracked_object.detection.bbox.x2) / 2.0
                centroid_y = (tracked_object.detection.bbox.y1 + tracked_object.detection.bbox.y2) / 2.0
                centroid = Point2D(x=centroid_x, y=centroid_y)

                # Update Re-ID manager
                visitor_id, is_returning = self.reid_manager.update(
                    track_id=tracked_object.track_id,
                    centroid=centroid,
                    confidence=tracked_object.detection.confidence,
                    frame_number=frame.frame_number,
                )

                # Update tracked object with visitor_id
                tracked_object.visitor_id = visitor_id
                tracked_object.metadata["is_returning"] = is_returning

                # Staff detection
                is_staff = self.staff_detector.is_staff(
                    tracked_object.detection.bbox,
                    visitor_id=visitor_id,
                )
                tracked_object.detection = replace(
                    tracked_object.detection,
                    is_staff=is_staff,
                )

            # Generate entry/exit events (line crossing)
            for tracked_object in tracked_objects:
                events = self.event_generator.update(
                    store_id=self.store_id,
                    camera_id=self.camera_id,
                    tracked_object=tracked_object,
                    frame_number=frame.frame_number,
                )

                if events:
                    print(
                        f"EVENTS GENERATED={len(events)} "
                        f"TRACK_ID={tracked_object.track_id}"
                    )

                # Generate zone events
                zone_events = self.zone_tracker.update(
                    visitor_id=tracked_object.visitor_id,
                    bbox=tracked_object.detection.bbox,
                    frame_number=frame.frame_number,
                    is_staff=tracked_object.detection.is_staff,
                )

                # 1. Publish natural zone events first
                for zone_event in zone_events:
                    print(
                        f"PUBLISHING ZONE EVENT -> "
                        f"{zone_event.event_type.value} zone={zone_event.zone_id}"
                    )

                    await self.publisher.publish(zone_event)
                    total_events += 1

                    logger.info(
                        "cv_zone_event_generated",
                        extra={
                            "visitor_id": zone_event.visitor_id,
                            "zone_id": zone_event.zone_id,
                            "event_type": zone_event.event_type.value,
                            "frame_number": frame.frame_number,
                        },
                    )

                # 2. Check for EXIT and clean up zones (fixes Ghost Queue)
                # We emit synthetic ZONE_EXIT events BEFORE the actual EXIT event
                synthetic_exits = []
                for event in events:
                    if event.event_type == EventType.EXIT:
                        final_zone_events = self.zone_tracker.cleanup_visitor(
                            visitor_id=tracked_object.visitor_id,
                            frame_number=frame.frame_number,
                            is_staff=tracked_object.detection.is_staff
                        )
                        synthetic_exits.extend(final_zone_events)
                        
                for z_event in synthetic_exits:
                    print(
                        f"PUBLISHING SYNTHETIC ZONE EXIT -> "
                        f"{z_event.event_type.value} zone={z_event.zone_id}"
                    )
                    await self.publisher.publish(z_event)
                    total_events += 1
                    logger.info(
                        "cv_zone_event_generated",
                        extra={
                            "visitor_id": z_event.visitor_id,
                            "zone_id": z_event.zone_id,
                            "event_type": z_event.event_type.value,
                            "frame_number": frame.frame_number,
                        },
                    )

                # 3. Publish line-crossing events LAST
                for event in events:
                    if event.event_type == EventType.EXIT:
                        self.reid_manager.mark_track_exited(
                            track_id=tracked_object.track_id,
                            frame_number=frame.frame_number
                        )

                    print(
                        f"PUBLISHING EVENT -> "
                        f"{event.event_type.value}"
                    )

                    await self.publisher.publish(event)
                    total_events += 1

                    logger.info(
                        "cv_event_generated",
                        extra={
                            "track_id": tracked_object.track_id,
                            "visitor_id": tracked_object.visitor_id,
                            "camera_id": self.camera_id,
                            "event_type": event.event_type.value,
                            "confidence": tracked_object.detection.confidence,
                            "frame_number": frame.frame_number,
                        },
                    )

            self.event_generator.prune(frame.frame_number)
            self.reid_manager.prune_old_trajectories(frame.frame_number)

            if self.debug_visualization and self.visualizer is not None:
                self.visualizer.draw(
                    frame.image,
                    tracked_objects,
                    self.event_generator.config,
                )

            latency_ms = round(
                (perf_counter() - started_at) * 1000,
                2,
            )

            logger.info(
                "cv_frame_processed",
                extra={
                    "track_id": (
                        tracked_objects[0].track_id
                        if tracked_objects
                        else None
                    ),
                    "visitor_id": (
                        tracked_objects[0].visitor_id
                        if tracked_objects
                        else None
                    ),
                    "camera_id": self.camera_id,
                    "event_type": None,
                    "confidence": (
                        tracked_objects[0].detection.confidence
                        if tracked_objects
                        else None
                    ),
                    "frame_number": frame.frame_number,
                    "latency_ms": latency_ms,
                },
            )

        print("=== PIPELINE FINISHED ===")
        print(f"TOTAL EVENTS GENERATED = {total_events}")

        return total_events
