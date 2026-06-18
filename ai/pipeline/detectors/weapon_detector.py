from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from tqdm import tqdm
from ultralytics import YOLO

from ..base import BaseDetector, DetectorResult


class WeaponDetector(BaseDetector):
    name = "weapon_detection"
    modality = "frame"

    def __init__(self, weights_path: str, sample_fps: int = 2) -> None:
        self.weights_path = weights_path
        self.sample_fps = sample_fps
        self.device = "cpu"
        self.model = None

    def load(self, device: str) -> None:
        self.device = device
        print(f"[Weapon] Loading YOLO weapon model from {self.weights_path}...")
        self.model = YOLO(self.weights_path)

    def predict(self, video_path: str, **kwargs) -> Optional[DetectorResult]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        sample_interval = max(1, int(fps / self.sample_fps))
        sampled_scores: list[tuple[int, float]] = []
        sampled_boxes: list[tuple[int, list[dict]]] = []

        print(f"[Weapon] Running weapon detection (sampling every {sample_interval} frames)...")
        frame_idx = 0
        pbar = tqdm(total=total_frames, desc="Weapon-det")
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_interval == 0:
                results = self.model(frame, verbose=False, conf=0.25)
                max_conf = 0.0
                boxes_this_frame = []
                if results[0].boxes is not None and len(results[0].boxes) > 0:
                    confs = results[0].boxes.conf.cpu().numpy()
                    xyxy = results[0].boxes.xyxy.cpu().numpy()
                    max_conf = float(confs.max())
                    boxes_this_frame = [
                        {"xyxy": box.tolist(), "conf": float(c)}
                        for box, c in zip(xyxy, confs)
                    ]
                sampled_scores.append((frame_idx, max_conf))
                sampled_boxes.append((frame_idx, boxes_this_frame))

            frame_idx += 1
            pbar.update(1)
        pbar.close()
        cap.release()

        frame_scores = np.zeros(total_frames, dtype=np.float32)
        frame_boxes: list[list[dict]] = [[] for _ in range(total_frames)]
        for i, (fidx, score) in enumerate(sampled_scores):
            next_fidx = sampled_scores[i + 1][0] if i + 1 < len(sampled_scores) else total_frames
            frame_scores[fidx:next_fidx] = score
            boxes = sampled_boxes[i][1]
            for f in range(fidx, next_fidx):
                frame_boxes[f] = boxes

        return DetectorResult(
            scores=frame_scores,
            num_frames=total_frames,
            metadata={"sample_interval": sample_interval, "frame_boxes": frame_boxes},
        )
