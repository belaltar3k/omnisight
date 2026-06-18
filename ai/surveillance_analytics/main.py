from __future__ import annotations

import argparse
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from surveillance_analytics.config import SmartCityConfig
from surveillance_analytics.core.engine import VideoEngine


def main():
    parser = argparse.ArgumentParser(description="OmniSight Smart City Surveillance Platform")
    parser.add_argument("--source", default="0", help="Video source: file path, camera index, or RTSP URL")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--dashboard-port", type=int, default=8765)
    parser.add_argument("--no-dashboard", action="store_true", help="Disable web dashboard")
    parser.add_argument("--no-display", action="store_true", help="Disable cv2 window (headless)")
    parser.add_argument("--no-output", action="store_true", help="Don't save output video")
    parser.add_argument("--disable", nargs="+", default=[], help="Module names to disable")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--yolo-model", default="yolov8n.pt", help="Primary YOLO model")
    parser.add_argument("--conf", type=float, default=0.35, help="YOLO confidence threshold")
    parser.add_argument("--demo", action="store_true", help="Run demo mode on sample video")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("surveillance_analytics")

    config = SmartCityConfig(
        video_source=args.source,
        device=args.device,
        yolo_model=args.yolo_model,
        yolo_conf=args.conf,
        disabled_modules=args.disable,
        output_dir=args.output_dir,
        save_output_video=not args.no_output,
        dashboard_port=args.dashboard_port,
    )

    if args.demo:
        ai_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in ["test.mp4", "shehab.mp4", "sneaky.mp4", "shoot.mp4"]:
            test_path = os.path.join(ai_dir, name)
            if os.path.isfile(test_path):
                config.video_source = test_path
                logger.info("Demo mode: using %s", test_path)
                break

    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(config.alert_frames_dir, exist_ok=True)

    # Start dashboard in background
    dashboard_update = None
    if not args.no_dashboard:
        try:
            from surveillance_analytics.dashboard.server import start_dashboard, update_dashboard_data
            dashboard_thread = threading.Thread(
                target=start_dashboard,
                args=(config,),
                daemon=True,
            )
            dashboard_thread.start()
            dashboard_update = update_dashboard_data
            logger.info("Dashboard running at http://localhost:%d", config.dashboard_port)
        except Exception as e:
            logger.warning("Dashboard failed to start: %s", e)

    logger.info("=" * 60)
    logger.info("OmniSight Smart City Surveillance Platform")
    logger.info("=" * 60)
    logger.info("Source: %s", config.video_source)
    logger.info("Device: %s", config.device)
    logger.info("Output: %s", config.output_dir)
    logger.info("Controls: H=heatmap  Z=zones  A=alerts  S=screenshot  Q=quit")
    logger.info("=" * 60)

    engine = VideoEngine(config)
    if dashboard_update:
        engine.set_dashboard_callback(dashboard_update)
    engine.run()


if __name__ == "__main__":
    main()
