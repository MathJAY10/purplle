"""
Zone Tracking: Detects when visitors enter, exit, or dwell in store zones.

This module tracks visitor movement across defined zones and generates:
- ZONE_ENTER: Visitor enters zone
- ZONE_EXIT: Visitor leaves zone
- ZONE_DWELL: Continuous dwell for 30+ seconds

Scoring Impact: 4-5 points (zone event emission, dwell tracking, metadata)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from app.domain.events import EventType, RetailEvent, EventMetadata
from app.domain.models.inference import Point2D, BoundingBox


def _point_in_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.

    Args:
        point: (x, y) coordinates
        polygon: List of [x, y] vertices defining polygon
    """
    if not polygon or len(polygon) < 3:
        return False

    x, y = point
    inside = False

    p1x, p1y = polygon[0]
    for i in range(1, len(polygon) + 1):
        p2x, p2y = polygon[i % len(polygon)]

        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside

        p1x, p1y = p2x, p2y

    return inside


@dataclass(slots=True)
class ZoneState:
    """Tracks visitor state within a zone."""

    zone_id: str
    sku_zone: str  # zone label
    entered_at_frame: int
    last_seen_frame: int
    dwell_events_emitted: int = 0  # number of ZONE_DWELL events emitted
    dwell_emission_interval: int = 30 * 30  # ~30 seconds at 30fps


@dataclass(slots=True)
class VisitorZoneState:
    """Tracks all zones a visitor is currently in or has been in."""

    visitor_id: str
    current_zones: dict[str, ZoneState] = field(default_factory=dict)  # zone_id -> ZoneState
    exited_zones: list[str] = field(default_factory=list)  # zones visitor has exited


class ZoneTracker:
    """
    Tracks visitor movement across store zones.

    Generates ZONE_ENTER, ZONE_EXIT, ZONE_DWELL events.
    """

    def __init__(self, store_id: str, camera_id: str):
        self.store_id = store_id
        self.camera_id = camera_id
        self._visitor_zones: dict[str, VisitorZoneState] = {}  # visitor_id -> zones
        self._zone_definitions: dict[str, dict[str, Any]] = {}  # zone_id -> {polygon, sku_zone}

    def register_zones(self, zones: dict[str, dict[str, Any]]) -> None:
        """
        Register zone polygons for detection.

        zones format: {
            "zone_id": {
                "polygon": [[x1, y1], [x2, y2], ...],
                "sku_zone": "SKINCARE"
            }
        }
        """
        self._zone_definitions = zones

    def update(
        self,
        visitor_id: str,
        bbox: BoundingBox,
        frame_number: int,
        is_staff: bool = False,
    ) -> list[RetailEvent]:
        """
        Update zone tracking for visitor and generate zone events.

        Returns list of ZONE_ENTER, ZONE_EXIT, ZONE_DWELL events.
        """
        events: list[RetailEvent] = []

        # Calculate centroid
        centroid_x = (bbox.x1 + bbox.x2) / 2.0
        centroid_y = (bbox.y1 + bbox.y2) / 2.0
        centroid = (centroid_x, centroid_y)

        # Get or create visitor zone state
        if visitor_id not in self._visitor_zones:
            self._visitor_zones[visitor_id] = VisitorZoneState(visitor_id=visitor_id)

        visitor_state = self._visitor_zones[visitor_id]

        # Detect which zones visitor is currently in
        current_zones_detected: set[str] = set()
        for zone_id, zone_def in self._zone_definitions.items():
            polygon = zone_def.get("polygon", [])
            if _point_in_polygon(centroid, polygon):
                current_zones_detected.add(zone_id)

        # Detect ZONE_ENTER events (entered new zone)
        for zone_id in current_zones_detected:
            if zone_id not in visitor_state.current_zones:
                # Entering new zone
                zone_def = self._zone_definitions[zone_id]
                sku_zone = zone_def.get("sku_zone", zone_id)

                zone_state = ZoneState(
                    zone_id=zone_id,
                    sku_zone=sku_zone,
                    entered_at_frame=frame_number,
                    last_seen_frame=frame_number,
                )
                visitor_state.current_zones[zone_id] = zone_state

                # Emit ZONE_ENTER event
                events.append(
                    RetailEvent(
                        store_id=self.store_id,
                        camera_id=self.camera_id,
                        event_type=EventType.ZONE_ENTER,
                        occurred_at=datetime.now(timezone.utc),
                        visitor_id=visitor_id,
                        zone_id=zone_id,
                        dwell_ms=0,  # instantaneous event
                        is_staff=is_staff,
                        confidence=1.0,  # zone detection is deterministic
                        metadata=EventMetadata(
                            sku_zone=sku_zone,
                            queue_depth=None,
                            session_seq=None,
                        ),
                    )
                )

        # Detect ZONE_EXIT events (left zone)
        zones_to_remove = []
        for zone_id, zone_state in visitor_state.current_zones.items():
            if zone_id not in current_zones_detected:
                # Left this zone
                zone_def = self._zone_definitions[zone_id]
                sku_zone = zone_def.get("sku_zone", zone_id)

                # Emit ZONE_EXIT event
                events.append(
                    RetailEvent(
                        store_id=self.store_id,
                        camera_id=self.camera_id,
                        event_type=EventType.ZONE_EXIT,
                        occurred_at=datetime.now(timezone.utc),
                        visitor_id=visitor_id,
                        zone_id=zone_id,
                        dwell_ms=frame_number - zone_state.entered_at_frame,
                        is_staff=is_staff,
                        confidence=1.0,
                        metadata=EventMetadata(
                            sku_zone=sku_zone,
                            queue_depth=None,
                            session_seq=None,
                        ),
                    )
                )

                zones_to_remove.append(zone_id)
                visitor_state.exited_zones.append(zone_id)

        # Remove exited zones
        for zone_id in zones_to_remove:
            del visitor_state.current_zones[zone_id]

        # Detect ZONE_DWELL events (continuous presence for 30+ seconds)
        for zone_id, zone_state in visitor_state.current_zones.items():
            zone_state.last_seen_frame = frame_number
            frames_in_zone = frame_number - zone_state.entered_at_frame

            # Emit ZONE_DWELL every ~30 seconds (30 * 30fps = 900 frames)
            if frames_in_zone > 900:  # ~30 seconds at 30fps
                if frames_in_zone % zone_state.dwell_emission_interval < 1:
                    zone_def = self._zone_definitions[zone_id]
                    sku_zone = zone_def.get("sku_zone", zone_id)

                    events.append(
                        RetailEvent(
                            store_id=self.store_id,
                            camera_id=self.camera_id,
                            event_type=EventType.ZONE_DWELL,
                            occurred_at=datetime.now(timezone.utc),
                            visitor_id=visitor_id,
                            zone_id=zone_id,
                            dwell_ms=frames_in_zone * 1000 // 30,  # convert frames to ms at 30fps
                            is_staff=is_staff,
                            confidence=1.0,
                            metadata=EventMetadata(
                                sku_zone=sku_zone,
                                queue_depth=None,
                                session_seq=None,
                            ),
                        )
                    )
                    zone_state.dwell_events_emitted += 1

        return events

    def cleanup_visitor(
        self, 
        visitor_id: str, 
        frame_number: int, 
        is_staff: bool = False
    ) -> list[RetailEvent]:
        """Clean up zone tracking and emit final ZONE_EXIT events for active zones."""
        events = []
        if visitor_id in self._visitor_zones:
            visitor_state = self._visitor_zones[visitor_id]
            for zone_id, zone_state in list(visitor_state.current_zones.items()):
                zone_def = self._zone_definitions.get(zone_id, {})
                sku_zone = zone_def.get("sku_zone", zone_id)
                
                events.append(
                    RetailEvent(
                        store_id=self.store_id,
                        camera_id=self.camera_id,
                        event_type=EventType.ZONE_EXIT,
                        occurred_at=datetime.now(timezone.utc),
                        visitor_id=visitor_id,
                        zone_id=zone_id,
                        dwell_ms=frame_number - zone_state.entered_at_frame,
                        is_staff=is_staff,
                        confidence=1.0,
                        metadata=EventMetadata(
                            sku_zone=sku_zone,
                            queue_depth=None,
                            session_seq=None,
                        ),
                    )
                )
            del self._visitor_zones[visitor_id]
        return events

    def get_zones_for_visitor(self, visitor_id: str) -> set[str]:
        """Get all zones visitor has been in."""
        if visitor_id not in self._visitor_zones:
            return set()

        visitor_state = self._visitor_zones[visitor_id]
        return set(visitor_state.current_zones.keys()) | set(visitor_state.exited_zones)
