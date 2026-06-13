"""
Run the MTMCT inference pipeline from the scripts directory.

Usage:
    python scripts/run_tracking.py --videos cam1.mp4 cam2.mp4
    python scripts/run_tracking.py --videos cam1.mp4 --yolo-model yolov8m.pt
"""

import argparse
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ai.components.tracking.config import Config
from ai.components.tracking.inference import run_inference


def main():
    parser = argparse.ArgumentParser(description="Run MTMCT tracking pipeline.")
    parser.add_argument("--videos", nargs="+", required=True, help="Video file paths or RTSP URLs")
    parser.add_argument("--yolo-model", default=None, help="Path to YOLO model weights")
    parser.add_argument("--db-path", default=None, help="Path for SQLite identity database")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug output")
    parser.add_argument("--face-threshold", type=float, default=None)
    parser.add_argument("--appearance-threshold", type=float, default=None)
    args = parser.parse_args()

    cfg = Config()
    if args.yolo_model:
        cfg.yolo_model = args.yolo_model
    if args.db_path:
        cfg.db_path = args.db_path
    if args.no_debug:
        cfg.debug_scores = False
        cfg.debug_show_rejections = False
    if args.face_threshold is not None:
        cfg.face_threshold = args.face_threshold
    if args.appearance_threshold is not None:
        cfg.appearance_threshold = args.appearance_threshold

    run_inference(args.videos, cfg)


if __name__ == "__main__":
    main()
