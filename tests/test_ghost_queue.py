import pytest
from app.cv.zone_tracker import ZoneTracker
from app.domain.events import EventType
from app.domain.models.inference import Point2D, BoundingBox

def test_ghost_queue_cleanup():
    # Setup
    tracker = ZoneTracker(store_id="test", camera_id="test")
    tracker.register_zones({
        "billing": {
            "polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
            "sku_zone": "billing"
        }
    })
    
    # 1. Visitor enters billing zone
    bbox = BoundingBox(x1=2.0, y1=2.0, x2=4.0, y2=4.0)  # Centroid (3, 3) is inside billing
    events = tracker.update(visitor_id="v1", bbox=bbox, frame_number=10)
    
    assert len(events) == 1
    assert events[0].event_type == EventType.ZONE_ENTER
    assert events[0].zone_id == "billing"
    
    # 2. Visitor exits store while still inside billing zone
    # This simulates processor calling cleanup_visitor when EXIT event is detected
    cleanup_events = tracker.cleanup_visitor(visitor_id="v1", frame_number=20, is_staff=False)
    
    assert len(cleanup_events) == 1
    assert cleanup_events[0].event_type == EventType.ZONE_EXIT
    assert cleanup_events[0].zone_id == "billing"
    assert cleanup_events[0].dwell_ms == 10  # 20 - 10 frames
    
    # 3. Verify ghost queue is cleared
    assert "v1" not in tracker._visitor_zones
    
    # If update is mistakenly called again, it's a new enter
    events_after = tracker.update(visitor_id="v1", bbox=bbox, frame_number=30)
    assert len(events_after) == 1
    assert events_after[0].event_type == EventType.ZONE_ENTER
