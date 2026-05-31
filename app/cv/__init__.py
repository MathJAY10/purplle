"""Computer vision pipeline package."""

from app.cv.crossing import LineCrossingEventGenerator, LineCrossingConfig
from app.cv.detector import DetectorService
from app.cv.processor import FrameProcessor
from app.cv.tracker import TrackerService
from app.cv.video import VideoStreamReader

__all__ = [
    "DetectorService",
    "FrameProcessor",
    "LineCrossingConfig",
    "LineCrossingEventGenerator",
    "TrackerService",
    "VideoStreamReader",
]
