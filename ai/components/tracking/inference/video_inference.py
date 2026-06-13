"""
Multi-Target Multi-Camera Tracking (MTMCT) video inference.

Fuses YOLO tracking + InsightFace face recognition + OSNet Re-ID appearance
features to assign persistent Global IDs across multiple cameras.

Usage:
    python -m ai.components.tracking.inference.video_inference --videos cam1.mp4 cam2.mp4
    python inference/video_inference.py --videos cam1.mp4 --yolo-model yolov8s.pt
"""

import argparse
import os
import sys
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

__package__ = "ai.components.tracking.inference"

import cv2
import numpy as np
from ultralytics import YOLO

from ..config import Config
from ..models import (
    FeatureExtractorEngine,
    DatabaseManager,
    IdentityFusionManager,
    PersonConfidenceTracker,
)
from ..models.filters import is_valid_person_detection, is_person_by_appearance
from ..models.streamer import MultiCameraStreamer


class MTMCTPipeline:
    """Orchestrates YOLO tracking, feature extraction, and identity fusion."""

    def __init__(self, video_sources: list[str], cfg: Config | None = None) -> None:
        if cfg is None:
            cfg = Config()
        self.cfg = cfg

        print(f"[INIT] Loading YOLO model from: {cfg.yolo_model}")
        self.yolo = YOLO(cfg.yolo_model)

        print("[INIT] Loading feature extractors (InsightFace + OSNet)...")
        self.feature_engine = FeatureExtractorEngine(cfg)

        print("[INIT] Initializing database...")
        self.db_manager = DatabaseManager(cfg)

        self.fusion_manager = IdentityFusionManager(self.feature_engine, self.db_manager, cfg)
        self.confidence_tracker = PersonConfidenceTracker(cfg)

        self.custom_tracker_yaml = self._create_custom_tracker_config()
        self._warmup_models()

        print("[INIT] Starting camera streams...")
        self.streamer = MultiCameraStreamer(video_sources)

    def _create_custom_tracker_config(self) -> str:
        yaml_path = os.path.join(os.path.dirname(__file__), "bytetrack_custom.yaml")
        tracker_yaml = (
            f"tracker_type: {self.cfg.tracker_type}\n"
            f"track_high_thresh: {self.cfg.track_high_thresh}\n"
            f"track_low_thresh: {self.cfg.track_low_thresh}\n"
            f"new_track_thresh: {self.cfg.new_track_thresh}\n"
            f"track_buffer: {self.cfg.track_buffer}\n"
            f"match_thresh: {self.cfg.match_thresh}\n"
            f"fuse_score: {self.cfg.fuse_score}"
        )
        with open(yaml_path, "w") as f:
            f.write(tracker_yaml)
        print(f"[INIT] Generated custom tracker config: {yaml_path}")
        return yaml_path

    def _warmup_models(self) -> None:
        print("[INIT] Warming up models (this may take a few seconds)...")
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        self.yolo.track(
            dummy, persist=True, classes=list(self.cfg.yolo_classes),
            conf=0.80, tracker=self.custom_tracker_yaml, verbose=False
        )
        self.feature_engine.extract_features(dummy)
        print("[INIT] Warm-up complete.")

    def _deduplicate_boxes(self, track_ids, xyxy_list):
        def iou(a, b):
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            ix1, iy1 = max(ax1, bx1), max(ay1, by1)
            ix2, iy2 = min(ax2, bx2), min(ay2, by2)
            iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
            inter = iw * ih
            area_a = (ax2 - ax1) * (ay2 - ay1)
            area_b = (bx2 - bx1) * (by2 - by1)
            union = area_a + area_b - inter
            return inter / union if union > 0 else 0.0

        keep_ids, keep_boxes = [], []
        used = [False] * len(xyxy_list)
        for i, box_i in enumerate(xyxy_list):
            if used[i]:
                continue
            for j in range(i + 1, len(xyxy_list)):
                if not used[j] and iou(box_i, xyxy_list[j]) > self.cfg.iou_dedup_thresh:
                    used[j] = True
            keep_ids.append(track_ids[i])
            keep_boxes.append(box_i)
        return keep_ids, keep_boxes

    def _process_frame(self, camera_id: str, frame: np.ndarray) -> np.ndarray:
        results = self.yolo.track(
            frame, persist=True, classes=list(self.cfg.yolo_classes),
            conf=self.cfg.yolo_conf, tracker=self.custom_tracker_yaml, verbose=False
        )

        if results[0].boxes is None or results[0].boxes.id is None:
            return frame

        boxes = results[0].boxes
        track_ids = boxes.id.int().cpu().tolist()
        xyxy_list = boxes.xyxy.int().cpu().tolist()

        track_ids, xyxy_list = self._deduplicate_boxes(track_ids, xyxy_list)

        active_track_ids = set(track_ids)
        self.fusion_manager.cleanup_stale_tracks(camera_id, active_track_ids)
        self.confidence_tracker.cleanup(camera_id, active_track_ids)

        for track_id, xyxy in zip(track_ids, xyxy_list):
            x1, y1, x2, y2 = xyxy
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            valid, reason1 = is_valid_person_detection(x1, y1, x2, y2, crop, self.cfg)
            if not valid:
                if self.cfg.debug_show_rejections:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 1)
                    cv2.putText(
                        frame, reason1[:30], (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1,
                    )
                if self.cfg.debug_scores:
                    print(f"[REJECT] cam={camera_id} track={track_id}: {reason1}")
                self.confidence_tracker.reset(camera_id, track_id)
                continue

            valid, reason2 = is_person_by_appearance(crop, self.cfg)
            if not valid:
                if self.cfg.debug_show_rejections:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 100, 200), 1)
                    cv2.putText(
                        frame, reason2[:30], (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 100, 200), 1,
                    )
                if self.cfg.debug_scores:
                    print(f"[REJECT] cam={camera_id} track={track_id}: {reason2}")
                self.confidence_tracker.reset(camera_id, track_id)
                continue

            confirmed = self.confidence_tracker.tick(camera_id, track_id)
            if not confirmed:
                if self.cfg.debug_show_rejections:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 200), 1)
                continue

            global_id = self.fusion_manager.resolve_identity(camera_id, track_id, crop)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"ID: {global_id}"
            cv2.putText(
                frame, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
            )

        return frame

    def run(self) -> None:
        print("[RUN] Pipeline started. Press 'q' to quit.")
        while True:
            frames = self.streamer.get_frames()
            if not frames:
                time.sleep(0.01)
                continue

            for camera_id, frame in frames:
                annotated_frame = self._process_frame(camera_id, frame)
                cv2.imshow(f"MTMCT - {camera_id}", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.streamer.stop()
        cv2.destroyAllWindows()
        print("[DONE] Pipeline stopped.")


def run_inference(
    video_sources: list[str],
    cfg: Config | None = None,
) -> None:
    """
    Run the MTMCT tracking pipeline on one or more video sources.

    Args:
        video_sources: list of video file paths or RTSP URLs
        cfg: optional Config override
    """
    if cfg is None:
        cfg = Config()
    pipeline = MTMCTPipeline(video_sources, cfg)
    pipeline.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MTMCT tracking inference.")
    parser.add_argument("--videos", nargs="+", required=True, help="Video file paths or RTSP URLs")
    parser.add_argument("--yolo-model", default=None, help="Path to YOLO model weights")
    parser.add_argument("--db-path", default=None, help="Path for SQLite identity database")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug output")
    args = parser.parse_args()

    cfg = Config()
    if args.yolo_model:
        cfg.yolo_model = args.yolo_model
    if args.db_path:
        cfg.db_path = args.db_path
    if args.no_debug:
        cfg.debug_scores = False
        cfg.debug_show_rejections = False

    run_inference(args.videos, cfg)
