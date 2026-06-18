from __future__ import annotations

import logging
from collections import deque
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F

from .base import FrameResult, StreamingDetector

logger = logging.getLogger(__name__)


class SkelNetStreamingDetector(StreamingDetector):
    name = "crime_skelnet"
    modality = "video"

    def __init__(
        self,
        weights_path: str,
        pose_model: str,
        clip_seconds: float = 4.0,
        target_fps: int = 15,
        max_bodies: int = 2,
        target_frames: int = 32,
    ):
        self.weights_path = weights_path
        self.pose_model_path = pose_model
        self.clip_seconds = clip_seconds
        self.target_fps = target_fps
        self.max_bodies = max_bodies
        self.target_frames = target_frames
        self.device = "cpu"

        self.model = None
        self.yolo = None
        self.cfg = None
        self.compute_bone = None
        self.compute_motion = None
        self.compute_angle = None

        window_size = int(clip_seconds * target_fps)
        self._window_size = window_size
        self._step = max(1, target_fps // 2)

        self._skeleton_buffer: deque[dict[int, np.ndarray]] = deque(maxlen=window_size)
        self._bbox_buffer: deque[dict[int, np.ndarray]] = deque(maxlen=window_size)
        self._frames_since_infer = 0
        self._last_score = 0.0
        self._last_track_ids: list[int] = []

    def load(self, device: str) -> None:
        from ultralytics import YOLO
        from components.crime_skelnet.config import Config
        from components.crime_skelnet.data import compute_bone, compute_motion, compute_angle
        from components.crime_skelnet.models import CrimeSkelNet

        self.device = device
        self.cfg = Config()
        self.compute_bone = compute_bone
        self.compute_motion = compute_motion
        self.compute_angle = compute_angle

        logger.info("Loading CrimeSkelNet from %s", self.weights_path)
        self.model = CrimeSkelNet(
            num_classes=self.cfg.num_classes, num_streams=self.cfg.num_streams
        ).to(device)
        ckpt = torch.load(self.weights_path, map_location=device, weights_only=False)
        state_dict = self._extract_and_normalize(ckpt)
        self.model.load_state_dict(state_dict, strict=False)
        self.model.eval()

        logger.info("Loading YOLOv8x-pose from %s", self.pose_model_path)
        self.yolo = YOLO(self.pose_model_path)

    @staticmethod
    def _extract_and_normalize(ckpt: dict) -> dict:
        if isinstance(ckpt, dict):
            for key in ("model", "state_dict", "model_state_dict", "net", "ema"):
                if key in ckpt and isinstance(ckpt[key], dict):
                    ckpt = ckpt[key]
                    break
        return {k.replace("_orig_mod.", ""): v for k, v in ckpt.items()}

    def process_frame(
        self, frame: np.ndarray, frame_idx: int, timestamp: float
    ) -> Optional[FrameResult]:
        if self.model is None or self.yolo is None:
            return None

        results = self.yolo.track(
            frame, persist=True, tracker="botsort.yaml", verbose=False, conf=0.25
        )
        frame_dict: dict[int, np.ndarray] = {}
        bbox_dict: dict[int, np.ndarray] = {}

        if (
            len(results) > 0
            and results[0].boxes is not None
            and results[0].boxes.id is not None
            and results[0].keypoints is not None
        ):
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            kpts = results[0].keypoints.data.cpu().numpy()
            xyxys = results[0].boxes.xyxy.cpu().numpy()
            for t_id, kpt, xyxy in zip(ids, kpts, xyxys):
                frame_dict[t_id] = kpt
                bbox_dict[t_id] = xyxy

        self._skeleton_buffer.append(frame_dict)
        self._bbox_buffer.append(bbox_dict)
        self._frames_since_infer += 1

        if len(self._skeleton_buffer) < 8:
            return None

        if self._frames_since_infer < self._step:
            return FrameResult(
                score=self._last_score,
                metadata={"track_ids": self._last_track_ids, "bboxes": bbox_dict},
            )

        self._frames_since_infer = 0
        window = list(self._skeleton_buffer)

        id_counts: dict[int, int] = {}
        for fd in window:
            for t_id in fd:
                id_counts[t_id] = id_counts.get(t_id, 0) + 1
        top_ids = sorted(id_counts, key=lambda x: id_counts[x], reverse=True)[
            : self.max_bodies
        ]
        self._last_track_ids = top_ids

        if not top_ids:
            self._last_score = 0.0
            return FrameResult(score=0.0, metadata={"track_ids": [], "bboxes": bbox_dict})

        clip = np.zeros((len(window), self.max_bodies, 17, 3), dtype=np.float32)
        for t_idx, fd in enumerate(window):
            for m_idx, t_id in enumerate(top_ids):
                if t_id in fd:
                    clip[t_idx, m_idx] = fd[t_id]
                elif t_idx > 0:
                    clip[t_idx, m_idx] = clip[t_idx - 1, m_idx]

        if np.std(clip[:, :, :, :2], axis=0).sum() < 3.0:
            self._last_score = 0.0
            return FrameResult(
                score=0.0, metadata={"track_ids": top_ids, "bboxes": bbox_dict}
            )

        x_tensor = self._preprocess_clip(clip).to(self.device)
        with torch.no_grad():
            if self.device == "cuda":
                with torch.amp.autocast("cuda"):
                    prob = torch.softmax(self.model(x_tensor), dim=1)[0, 1].item()
            else:
                prob = torch.softmax(self.model(x_tensor), dim=1)[0, 1].item()

        self._last_score = prob
        return FrameResult(
            score=prob, metadata={"track_ids": top_ids, "bboxes": bbox_dict}
        )

    def _preprocess_clip(self, raw_clip: np.ndarray) -> torch.Tensor:
        joint = torch.tensor(
            raw_clip.transpose(3, 0, 2, 1).copy(), dtype=torch.float32
        )
        joint = torch.nan_to_num(joint, nan=0.0, posinf=0.0, neginf=0.0)

        conf = joint[2]
        mask = conf > 0
        center = (joint[:2, :, 11:12, :] + joint[:2, :, 12:13, :]) / 2.0
        joint[:2] -= center

        y = joint[1].clone()
        y[~mask] = -1e4
        h_max = y.amax(dim=1, keepdim=True)
        y[~mask] = 1e4
        h_min = y.amin(dim=1, keepdim=True)
        scale = (h_max - h_min).clamp(min=1.0)
        joint[:2] /= scale.unsqueeze(0)
        joint[:2] = joint[:2].clamp(-5.0, 5.0)

        invalid = conf.sum(dim=(0, 1)) < 1e-3
        if invalid.any():
            joint[:, :, :, invalid] = 0.0

        C, T, V, M = joint.shape
        if T != self.target_frames:
            xr = joint.permute(2, 3, 0, 1).reshape(V * M, C, T)
            xy_weighted = xr[:, :2, :] * xr[:, 2:3, :]
            xy_i = F.interpolate(
                xy_weighted,
                size=self.target_frames,
                mode="linear",
                align_corners=False,
            )
            cf_i = F.interpolate(
                xr[:, 2:3, :],
                size=self.target_frames,
                mode="linear",
                align_corners=False,
            )
            out = torch.cat([xy_i / (cf_i + 1e-5), cf_i], dim=1)
            joint = out.view(V, M, C, self.target_frames).permute(2, 3, 0, 1)

        joint = torch.nan_to_num(joint, nan=0.0)
        order = torch.argsort(joint[0].mean(dim=(0, 1)))
        joint = joint[:, :, :, order]

        bone = self.compute_bone(joint)
        eff_fps = self.target_frames / self.clip_seconds

        streams = torch.stack(
            [
                joint,
                bone,
                self.compute_motion(joint, eff_fps, self.cfg.base_fps),
                self.compute_motion(bone, eff_fps, self.cfg.base_fps),
                self.compute_angle(bone),
            ],
            dim=0,
        )

        return torch.nan_to_num(streams, nan=0.0).unsqueeze(0)

    def reset(self) -> None:
        self._skeleton_buffer.clear()
        self._bbox_buffer.clear()
        self._frames_since_infer = 0
        self._last_score = 0.0
        self._last_track_ids = []

    def get_metadata(self) -> dict:
        return {"track_ids": self._last_track_ids}
