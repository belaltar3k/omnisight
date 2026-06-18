from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from .base import FrameResult, StreamingDetector

logger = logging.getLogger(__name__)


class WeaponStreamingDetector(StreamingDetector):
    name = "weapon_detection"
    modality = "frame"

    def __init__(self, weights_path: str, sample_fps: int = 2, target_fps: int = 15):
        self.weights_path = weights_path
        self.sample_fps = sample_fps
        self.target_fps = target_fps
        self.device = "cpu"
        self.model = None
        self._last_score: float = 0.0
        self._last_boxes: list[dict] = []
        self._sample_interval: int = max(1, target_fps // sample_fps)

    def load(self, device: str) -> None:
        from ultralytics import YOLO

        self.device = device
        logger.info("Loading YOLO weapon model from %s", self.weights_path)
        self.model = YOLO(self.weights_path)

    def process_frame(
        self, frame: np.ndarray, frame_idx: int, timestamp: float
    ) -> Optional[FrameResult]:
        if self.model is None:
            return None

        if frame_idx % self._sample_interval != 0:
            return FrameResult(score=self._last_score, metadata={"boxes": self._last_boxes})

        results = self.model(frame, verbose=False, conf=0.25)
        max_conf = 0.0
        boxes = []

        if results[0].boxes is not None and len(results[0].boxes) > 0:
            confs = results[0].boxes.conf.cpu().numpy()
            xyxy = results[0].boxes.xyxy.cpu().numpy()
            max_conf = float(confs.max())
            boxes = [
                {"xyxy": box.tolist(), "conf": float(c)}
                for box, c in zip(xyxy, confs)
            ]

        self._last_score = max_conf
        self._last_boxes = boxes
        return FrameResult(score=max_conf, metadata={"boxes": boxes})

    def reset(self) -> None:
        self._last_score = 0.0
        self._last_boxes = []

    def get_metadata(self) -> dict:
        return {"boxes": self._last_boxes, "sample_interval": self._sample_interval}
