from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager

from app.cv.types import VideoFrame


class VideoStreamReader(AbstractContextManager["VideoStreamReader"]):
    def __init__(self, source: str, frame_skip: int = 1) -> None:
        self.source = source
        self.frame_skip = max(1, frame_skip)
        self._capture = None

    def __enter__(self) -> "VideoStreamReader":
        self._capture = self._open_capture()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _open_capture(self):
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("opencv-python-headless is required for video processing") from exc

        capture = cv2.VideoCapture(self.source)
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open video source: {self.source}")
        return capture

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def iter_frames(self) -> Iterator[VideoFrame]:
        if self._capture is None:
            self._capture = self._open_capture()

        frame_number = 0
        while True:
            ok, frame = self._capture.read()
            if not ok:
                break

            if frame_number % self.frame_skip == 0:
                yield VideoFrame(frame_number=frame_number, image=frame)
            frame_number += 1
