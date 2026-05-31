from __future__ import annotations

import asyncio
import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the store intelligence CV pipeline on an MP4 file")
    parser.add_argument("--video", required=True, help="Path to MP4 file")
    parser.add_argument("--store", dest="store_id", required=True, help="Store identifier")
    parser.add_argument("--camera", dest="camera_id", required=True, help="Camera identifier")
    parser.add_argument("--debug-visualization", action="store_true", help="Enable annotation rendering")
    return parser.parse_args()


async def main() -> None:
    from app.core.config import get_settings
    from app.core.store_config import StoreConfigLoader
    from app.cv.crossing import LineCrossingConfig, LineCrossingEventGenerator
    from app.cv.detector import DetectorService
    from app.cv.processor import FrameProcessor
    from app.cv.tracker import TrackerService
    from app.cv.video import VideoStreamReader
    from app.cv.visualization import DebugVisualizer
    from app.core.container import build_container

    args = parse_args()
    settings = get_settings()
    store_config = StoreConfigLoader(settings.store_config_dir).load(args.store_id)
    camera_config = next((camera for camera in store_config.cameras if camera.camera_id == args.camera_id), None)
    if camera_config is None:
        raise RuntimeError(f"Camera {args.camera_id} not found in store config {args.store_id}")

    container = build_container(settings)
    try:
        line = camera_config.entry_line
        line_config = LineCrossingConfig(
            x1=float(line[0]["x"]),
            y1=float(line[0]["y"]),
            x2=float(line[1]["x"]),
            y2=float(line[1]["y"]),
            debounce_frames=settings.cv_debounce_frames,
            track_ttl_frames=settings.cv_track_ttl_frames,
        )
        detector = DetectorService(confidence_threshold=camera_config.thresholds.get("confidence", settings.cv_confidence_threshold))
        tracker = TrackerService(frame_rate=30)
        generator = LineCrossingEventGenerator(line_config)
        processor = FrameProcessor(
            detector=detector,
            tracker=tracker,
            event_generator=generator,
            publisher=container.event_publisher,
            store_id=args.store_id,
            camera_id=args.camera_id,
            debug_visualization=args.debug_visualization or settings.cv_debug_visualization,
            visualizer=DebugVisualizer() if (args.debug_visualization or settings.cv_debug_visualization) else None,
        )
        with VideoStreamReader(args.video, frame_skip=camera_config.frame_skip or settings.cv_frame_skip) as reader:
            await processor.process_video(reader)
    finally:
        await container.aclose()


if __name__ == "__main__":
    asyncio.run(main())