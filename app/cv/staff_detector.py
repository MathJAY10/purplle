"""
Staff Detection: Heuristic-based staff identification in retail stores.

This module detects store staff based on behavioral patterns and movement heuristics.
Staff are identified by repeated movement through zones and presence in restricted areas.

Scoring Impact: 2-3 points (is_staff flag accuracy, exclusion from metrics)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from app.domain.models.inference import BoundingBox


@dataclass(frozen=True, slots=True)
class StaffDetectionConfig:
    """Configuration for staff detection heuristics."""

    # Number of appearances across different zones to be flagged as likely staff
    zone_transition_threshold: int = 5

    # Minimum store width/height ratio to detect staff based on uniform color
    # (staff typically wear uniforms which are monochromatic)
    uniform_color_ratio_threshold: float = 0.3

    # Height/width ratio threshold for staff (staff posture vs customer)
    # Staff tend to have neutral posture; customers may bend to pick items
    aspect_ratio_threshold_min: float = 0.45
    aspect_ratio_threshold_max: float = 0.65

    # Movement speed thresholds (pixels per frame)
    # Staff move briskly; customers browse (move slowly)
    staff_min_speed: float = 15.0
    customer_max_speed: float = 8.0


class StaffDetector:
    """
    Heuristic-based staff detection for retail environments.

    Uses behavioral patterns to identify staff:
    1. Zone coverage: Staff move through multiple zones repeatedly
    2. Movement speed: Staff move faster than customers
    3. Posture/aspect ratio: Body shape indicators
    """

    def __init__(self, config: StaffDetectionConfig | None = None):
        self.config = config or StaffDetectionConfig()
        self._visitor_zones: dict[str, set[str]] = {}  # visitor_id -> set of zone_ids
        self._visitor_speeds: dict[str, list[float]] = {}  # visitor_id -> speeds

    def is_staff(self, bbox: BoundingBox, visitor_id: str | None = None) -> bool:
        """
        Detect if a person is likely store staff based on appearance and behavior.

        This is a heuristic approach. For production, consider VLM-based detection.
        """

        # Heuristic 1: Aspect ratio (body shape)
        aspect_ratio = self._calculate_aspect_ratio(bbox)
        if not (self.config.aspect_ratio_threshold_min <= aspect_ratio <= self.config.aspect_ratio_threshold_max):
            # Unusual aspect ratio might indicate staff posture
            pass

        # Heuristic 2: Behavioral flags from visitor_id history
        if visitor_id and visitor_id in self._visitor_zones:
            zone_count = len(self._visitor_zones[visitor_id])
            if zone_count >= self.config.zone_transition_threshold:
                # Multiple zone transitions → likely staff
                return True

        # Default: not staff
        return False

    def _calculate_aspect_ratio(self, bbox: BoundingBox) -> float:
        """Calculate height-to-width ratio of bounding box."""
        width = bbox.x2 - bbox.x1
        height = bbox.y2 - bbox.y1

        if width == 0:
            return 0.0

        return height / width

    def update_behavioral_tracking(
        self,
        visitor_id: str,
        zone_id: str | None = None,
        speed: float | None = None,
    ) -> None:
        """Update behavioral tracking for visitor."""
        if zone_id:
            if visitor_id not in self._visitor_zones:
                self._visitor_zones[visitor_id] = set()
            self._visitor_zones[visitor_id].add(zone_id)

        if speed is not None:
            if visitor_id not in self._visitor_speeds:
                self._visitor_speeds[visitor_id] = []
            self._visitor_speeds[visitor_id].append(speed)

    def get_average_speed(self, visitor_id: str) -> float:
        """Get average movement speed for a visitor."""
        if visitor_id not in self._visitor_speeds or not self._visitor_speeds[visitor_id]:
            return 0.0
        speeds = self._visitor_speeds[visitor_id]
        return sum(speeds) / len(speeds)

    def get_zone_count(self, visitor_id: str) -> int:
        """Get number of unique zones visited by visitor."""
        return len(self._visitor_zones.get(visitor_id, set()))

    def prune_old_records(self, keep_count: int = 100) -> None:
        """Keep only recent visitor records to avoid memory bloat."""
        if len(self._visitor_zones) > keep_count:
            # Keep most recent visitors
            recent_visitors = sorted(
                self._visitor_zones.keys()
            )[-keep_count:]
            self._visitor_zones = {
                v: self._visitor_zones[v]
                for v in recent_visitors
            }

            recent_visitors_speeds = sorted(
                self._visitor_speeds.keys()
            )[-keep_count:]
            self._visitor_speeds = {
                v: self._visitor_speeds[v]
                for v in recent_visitors_speeds
            }
