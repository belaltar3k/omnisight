from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm
from ultralytics import YOLO

from ..base import BaseDetector, DetectorResult


class SkelNetDetector(BaseDetector):
    name = "crime_skelnet"
    modality = "video"

    def __init__(self, weights_path: str, pose_model: str = "yolov8x-pose.pt") -> None:
        self.weights_path = weights_path
        self.pose_model_path = pose_model
        self.device = "cpu"
        self.model = None
        self.yolo = None

    def load(self, device: str) -> None:
        import sys, os
        comp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        if comp_root not in sys.path:
            sys.path.insert(0, comp_root)

        from components.crime_skelnet.config import Config
        from components.crime_skelnet.data import compute_bone, compute_motion, compute_angle
        from components.crime_skelnet.models import CrimeSkelNet

        self.device = device
        self.cfg = Config()
        self.compute_bone = compute_bone
        self.compute_motion = compute_motion
        self.compute_angle = compute_angle

        print(f"[SkelNet] Loading CrimeSkelNet from {self.weights_path}...")
        self.model = CrimeSkelNet(
            num_classes=self.cfg.num_classes, num_streams=self.cfg.num_streams
        ).to(device)

        ckpt = torch.load(self.weights_path, map_location=device, weights_only=False)
        state_dict = self._extract_and_normalize(ckpt)
        self.model.load_state_dict(state_dict, strict=False)
        self.model.eval()

        print(f"[SkelNet] Loading YOLOv8x-pose...")
        self.yolo = YOLO(self.pose_model_path)

    def _extract_and_normalize(self, ckpt: dict) -> dict:
        if isinstance(ckpt, dict):
            for key in ("model", "state_dict", "model_state_dict", "net", "ema"):
                if key in ckpt and isinstance(ckpt[key], dict):
                    ckpt = ckpt[key]
                    break
        return {k.replace("_orig_mod.", ""): v for k, v in ckpt.items()}

    def _preprocess_clip(self, raw_clip: np.ndarray) -> torch.Tensor:
        joint = torch.tensor(raw_clip.transpose(3, 0, 2, 1).copy(), dtype=torch.float32)
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
        if T != self.cfg.target_frames:
            xr = joint.permute(2, 3, 0, 1).reshape(V * M, C, T)
            xy_weighted = xr[:, :2, :] * xr[:, 2:3, :]
            xy_i = F.interpolate(xy_weighted, size=self.cfg.target_frames, mode="linear", align_corners=False)
            cf_i = F.interpolate(xr[:, 2:3, :], size=self.cfg.target_frames, mode="linear", align_corners=False)
            out = torch.cat([xy_i / (cf_i + 1e-5), cf_i], dim=1)
            joint = out.view(V, M, C, self.cfg.target_frames).permute(2, 3, 0, 1)

        joint = torch.nan_to_num(joint, nan=0.0)
        order = torch.argsort(joint[0].mean(dim=(0, 1)))
        joint = joint[:, :, :, order]

        bone = self.compute_bone(joint)
        eff_fps = self.cfg.target_frames / self.cfg.clip_seconds

        streams = torch.stack([
            joint,
            bone,
            self.compute_motion(joint, eff_fps, self.cfg.base_fps),
            self.compute_motion(bone, eff_fps, self.cfg.base_fps),
            self.compute_angle(bone),
        ], dim=0)

        return torch.nan_to_num(streams, nan=0.0).unsqueeze(0)

    def predict(self, video_path: str, **kwargs) -> Optional[DetectorResult]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_tracks: list[dict[int, np.ndarray]] = []
        frame_bboxes: list[dict[int, np.ndarray]] = []

        print(f"[SkelNet] Phase 1 — Extracting skeletons ({total_frames} frames)...")
        for _ in tqdm(range(total_frames), desc="SkelNet-pose"):
            ret, frame = cap.read()
            if not ret:
                break

            results = self.yolo.track(frame, persist=True, tracker="botsort.yaml", verbose=False, conf=0.25)
            frame_dict: dict[int, np.ndarray] = {}
            bbox_dict: dict[int, np.ndarray] = {}

            if (len(results) > 0
                    and results[0].boxes is not None
                    and results[0].boxes.id is not None
                    and results[0].keypoints is not None):
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                kpts = results[0].keypoints.data.cpu().numpy()
                xyxys = results[0].boxes.xyxy.cpu().numpy()
                for t_id, kpt, xyxy in zip(ids, kpts, xyxys):
                    frame_dict[t_id] = kpt
                    bbox_dict[t_id] = xyxy

            frame_tracks.append(frame_dict)
            frame_bboxes.append(bbox_dict)
        cap.release()

        T_total = len(frame_tracks)
        window_size = int(self.cfg.clip_seconds * fps)
        step = int(fps // 2)
        score_lists: list[list[float]] = [[] for _ in range(T_total)]

        print(f"[SkelNet] Phase 2 — Running CrimeSkelNet sliding window...")
        for start in tqdm(range(0, T_total, step), desc="SkelNet-infer"):
            end = min(start + window_size, T_total)
            if end - start < 8:
                continue

            window = frame_tracks[start:end]

            id_counts: dict[int, int] = {}
            for fd in window:
                for t_id in fd:
                    id_counts[t_id] = id_counts.get(t_id, 0) + 1
            top_ids = sorted(id_counts, key=lambda x: id_counts[x], reverse=True)[:self.cfg.max_bodies]

            if not top_ids:
                prob = 0.0
            else:
                clip = np.zeros((end - start, self.cfg.max_bodies, 17, 3), dtype=np.float32)
                for t_idx, fd in enumerate(window):
                    for m_idx, t_id in enumerate(top_ids):
                        if t_id in fd:
                            clip[t_idx, m_idx] = fd[t_id]
                        elif t_idx > 0:
                            clip[t_idx, m_idx] = clip[t_idx - 1, m_idx]

                if np.std(clip[:, :, :, :2], axis=0).sum() < 3.0:
                    prob = 0.0
                else:
                    x_tensor = self._preprocess_clip(clip).to(self.device)
                    with torch.no_grad(), torch.amp.autocast("cuda"):
                        prob = torch.softmax(self.model(x_tensor), dim=1)[0, 1].item()

            for i in range(start, end):
                score_lists[i].append(prob)

        frame_scores = np.array(
            [float(np.mean(s)) if s else 0.0 for s in score_lists],
            dtype=np.float32,
        )

        return DetectorResult(
            scores=frame_scores,
            num_frames=total_frames,
            metadata={"frame_tracks": frame_tracks, "frame_bboxes": frame_bboxes},
        )
