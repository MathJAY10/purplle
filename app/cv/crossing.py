from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid5, NAMESPACE_URL

from app.domain.events import EventType, RetailEvent
from app.domain.models.inference import TrackedObject


@dataclass(frozen=True, slots=True)
class LineCrossingConfig:
    x1: float
    y1: float
    x2: float
    y2: float
    debounce_frames: int = 15
    track_ttl_frames: int = 45


@dataclass(slots=True)
class TrackCrossingState:
    last_point: tuple[float, float] | None = None
    last_side: int | None = None
    last_event_frame: int | None = None
    last_seen_frame: int | None = None
    has_entered: bool = False


def _line_side(config: LineCrossingConfig, point: tuple[float, float]) -> int:
    px, py = point

    value = (
        (config.x2 - config.x1) * (py - config.y1)
        - (config.y2 - config.y1) * (px - config.x1)
    )

    if abs(value) < 1e-6:
        return 0

    return 1 if value > 0 else -1


def _centroid(tracked_object: TrackedObject) -> tuple[float, float]:
    bbox = tracked_object.detection.bbox

    return (
        (bbox.x1 + bbox.x2) / 2.0,
        (bbox.y1 + bbox.y2) / 2.0,
    )


@dataclass(slots=True)
class LineCrossingEventGenerator:
    config: LineCrossingConfig
    _track_states: dict[int, TrackCrossingState] = field(default_factory=dict)

    def update(
        self,
        *,
        store_id: str,
        camera_id: str,
        tracked_object: TrackedObject,
        frame_number: int,
    ) -> list[RetailEvent]:

        centroid = _centroid(tracked_object)
        current_side = _line_side(self.config, centroid)

        print(
            f"TRACK={tracked_object.track_id} "
            f"CENTROID={centroid} "
            f"SIDE={current_side}"
        )

        state = self._track_states.setdefault(
            tracked_object.track_id,
            TrackCrossingState(),
        )

        state.last_seen_frame = frame_number

        events: list[RetailEvent] = []

        if (
            state.last_point is not None
            and state.last_side is not None
            and current_side != 0
            and state.last_side != 0
            and current_side != state.last_side
        ):
            print(
                f"CROSSING DETECTED "
                f"TRACK={tracked_object.track_id} "
                f"OLD_SIDE={state.last_side} "
                f"NEW_SIDE={current_side}"
            )

            if (
                state.last_event_frame is None
                or frame_number - state.last_event_frame
                >= self.config.debounce_frames
            ):
                is_returning = tracked_object.metadata.get("is_returning", False)
                
                if state.last_side < current_side:
                    if is_returning and not state.has_entered:
                        event_type = EventType.REENTRY
                    else:
                        event_type = EventType.ENTRY
                    state.has_entered = True
                else:
                    event_type = EventType.EXIT

                payload = {
                    "track_id": tracked_object.track_id,
                    "bbox": {
                        "x1": tracked_object.detection.bbox.x1,
                        "y1": tracked_object.detection.bbox.y1,
                        "x2": tracked_object.detection.bbox.x2,
                        "y2": tracked_object.detection.bbox.y2,
                    },
                    "confidence": tracked_object.detection.confidence,
                    "frame_number": frame_number,
                    "direction": (
                        "in"
                        if event_type == EventType.ENTRY
                        else "out"
                    ),
                    "line": {
                        "x1": self.config.x1,
                        "y1": self.config.y1,
                        "x2": self.config.x2,
                        "y2": self.config.y2,
                    },
                }

                events.append(
                    RetailEvent(
                        idempotency_key=self._build_idempotency_key(
                            camera_id,
                            tracked_object.track_id,
                            event_type,
                            frame_number,
                        ),
                        store_id=store_id,
                        camera_id=camera_id,
                        event_type=event_type,
                        occurred_at=datetime.now(timezone.utc),
                        visitor_id=tracked_object.visitor_id,  # Re-ID token from tracker
                        track_id=str(tracked_object.track_id),
                        zone_id=None,  # null for ENTRY/EXIT events
                        dwell_ms=0,  # 0 for instantaneous events
                        is_staff=tracked_object.detection.is_staff,  # Staff classification flag
                        confidence=tracked_object.detection.confidence,  # Detection confidence
                        payload=payload,
                        metadata={},  # Queue depth, sku_zone handled in zone events
                    )
                )

                state.last_event_frame = frame_number

        state.last_point = centroid

        if current_side != 0:
            state.last_side = current_side

        return events

    def prune(self, frame_number: int) -> None:
        stale_track_ids = [
            track_id
            for track_id, state in self._track_states.items()
            if (
                state.last_seen_frame is not None
                and frame_number - state.last_seen_frame
                > self.config.track_ttl_frames
            )
        ]

        for track_id in stale_track_ids:
            self._track_states.pop(track_id, None)

    def _build_idempotency_key(
        self,
        camera_id: str,
        track_id: int,
        event_type: EventType,
        frame_number: int,
    ) -> str:
        seed = (
            f"{camera_id}:"
            f"{track_id}:"
            f"{event_type.value}:"
            f"{frame_number}"
        )

        return str(uuid5(NAMESPACE_URL, seed))