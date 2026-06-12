import math
import random
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset

# ── Skeleton topology ────────────────────────────────────────────────────────

BONE_PAIRS = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 6), (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

LEFT_JOINTS  = [1, 3,  5,  7,  9, 11, 13, 15]
RIGHT_JOINTS = [2, 4,  6,  8, 10, 12, 14, 16]


# ── Feature engineering ──────────────────────────────────────────────────────

def compute_bone(joint: torch.Tensor) -> torch.Tensor:
    """Joint displacement vectors along skeleton edges."""
    bone = torch.zeros_like(joint)
    for src, tgt in BONE_PAIRS:
        bone[:2, :, tgt, :] = joint[:2, :, tgt, :] - joint[:2, :, src, :]
        bone[2,  :, tgt, :] = torch.minimum(joint[2, :, tgt, :], joint[2, :, src, :])
    return bone


def compute_motion(
    x: torch.Tensor,
    effective_fps: float,
    base_fps: float,
) -> torch.Tensor:
    """Frame-to-frame velocity, normalised by the FPS ratio."""
    motion   = torch.zeros_like(x)
    dt_ratio = effective_fps / base_fps
    motion[:2, 1:] = ((x[:2, 1:] - x[:2, :-1]) * dt_ratio).clamp(-1.0, 1.0)
    motion[2,  1:] = torch.minimum(x[2, 1:], x[2, :-1])
    return motion


def compute_angle(bone: torch.Tensor) -> torch.Tensor:
    """Unit direction of each bone vector."""
    angle     = torch.zeros_like(bone)
    norm      = torch.norm(bone[:2], dim=0, keepdim=True) + 1e-5
    angle[:2] = bone[:2] / norm
    angle[2]  = bone[2]
    return angle


# ── Dataset ──────────────────────────────────────────────────────────────────

class SurveillanceDataset(Dataset):
    """
    Loads pre-compiled .npy clip files and returns a 5-stream tensor.

    Each sample shape: (5, C=3, T=target_frames, V=17, M=max_bodies)
    where the 5 streams are: joint · bone · joint-motion · bone-motion · angle.
    """

    def __init__(
        self,
        index_list: list[dict],
        config,
        mode: str = "train",
        val_clips: int = 3,
    ):
        self.index     = index_list
        self.cfg       = config
        self.mode      = mode
        self.val_clips = val_clips if mode == "val" else 1
        self._eff_fps  = config.target_frames / config.clip_seconds

    def __len__(self) -> int:
        return len(self.index)

    # ── Internal helpers ─────────────────────────────────────────

    def _sample_clip(
        self,
        raw_video: np.ndarray,
        T_raw: int,
        target_f: int,
        clip_idx: int = 0,
    ) -> np.ndarray:
        if T_raw <= target_f:
            return raw_video[:]

        max_start = T_raw - target_f

        if self.mode == "train":
            start = random.randint(0, max_start)
        else:
            if self.val_clips > 1:
                start = min(
                    int(round(clip_idx * (max_start / (self.val_clips - 1)))),
                    max_start,
                )
            else:
                start = max_start // 2

        return raw_video[start : start + target_f]

    def _normalise(self, joint: torch.Tensor) -> torch.Tensor:
        """Centre on hips, scale by body height, clamp outliers."""
        conf = joint[2]
        mask = conf > 0

        # Centre on hip midpoint
        center    = (joint[:2, :, 11:12, :] + joint[:2, :, 12:13, :]) / 2.0
        joint[:2] = joint[:2] - center

        # Scale by body height
        y          = joint[1].clone()
        y[~mask]   = -1e4
        h_max      = y.amax(dim=1, keepdim=True)
        y[~mask]   =  1e4
        h_min      = y.amin(dim=1, keepdim=True)
        scale      = (h_max - h_min).clamp(min=1.0)
        joint[:2]  = joint[:2] / scale.unsqueeze(0)
        joint[:2]  = joint[:2].clamp(-5.0, 5.0)

        # Zero out bodies with no detections
        invalid = conf.sum(dim=(0, 1)) < 1e-3
        if invalid.any():
            joint[:, :, :, invalid] = 0.0

        return joint

    def _resample(self, joint: torch.Tensor) -> torch.Tensor:
        """Confidence-weighted linear interpolation to target_frames."""
        C, T, V, M = joint.shape
        if T == self.cfg.target_frames:
            return joint

        xr         = joint.permute(2, 3, 0, 1).reshape(V * M, C, T)
        xy_weighted = xr[:, :2, :] * xr[:, 2:3, :]
        xy_i       = F.interpolate(xy_weighted, size=self.cfg.target_frames,
                                   mode="linear", align_corners=False)
        cf_i       = F.interpolate(xr[:, 2:3, :], size=self.cfg.target_frames,
                                   mode="linear", align_corners=False)
        out        = torch.cat([xy_i / (cf_i + 1e-5), cf_i], dim=1)
        joint      = out.view(V, M, C, self.cfg.target_frames).permute(2, 3, 0, 1)
        return torch.nan_to_num(joint, nan=0.0)

    def _augment(self, joint: torch.Tensor) -> torch.Tensor:
        """Training-time spatial augmentations."""
        cfg = self.cfg

        if cfg.aug_flip and random.random() < 0.5:
            joint[0] = -joint[0]
            l = joint[:, :, LEFT_JOINTS,  :].clone()
            r = joint[:, :, RIGHT_JOINTS, :].clone()
            joint[:, :, LEFT_JOINTS,  :] = r
            joint[:, :, RIGHT_JOINTS, :] = l

        if cfg.aug_rotate and random.random() < 0.5:
            ang   = random.uniform(-math.pi / 6, math.pi / 6)
            c, s  = math.cos(ang), math.sin(ang)
            R     = torch.tensor([[c, -s], [s, c]], dtype=joint.dtype)
            joint[:2] = (R @ joint[:2].reshape(2, -1)).reshape(2, *joint.shape[1:])

        if cfg.aug_scale and random.random() < 0.5:
            joint[:2] *= random.uniform(0.85, 1.15)

        if cfg.aug_joint_mask and random.random() < 0.3:
            joint[:, :, random.sample(range(17), 2), :] = 0.0
            conf_noise = torch.rand_like(joint[2]) < 0.1
            joint[:2][conf_noise.unsqueeze(0).expand(2, -1, -1, -1)] *= 0.2
            joint[2][conf_noise] *= 0.2

        return joint

    # ── Public interface ─────────────────────────────────────────

    def __getitem__(self, idx: int):
        item      = self.index[idx]
        raw_video = np.load(item["path"], mmap_mode="r")
        target_f  = max(8, int(self.cfg.clip_seconds * item["fps"]))

        clips_out = []
        for ci in range(self.val_clips):
            raw_clip = self._sample_clip(raw_video, item["T"], target_f, ci)

            joint = torch.tensor(
                raw_clip.transpose(3, 0, 2, 1).copy(), dtype=torch.float32
            )
            joint = torch.nan_to_num(joint, nan=0.0, posinf=0.0, neginf=0.0)
            joint = self._normalise(joint)
            joint = self._resample(joint)

            # Sort bodies by x-position for determinism
            order = torch.argsort(joint[0].mean(dim=(0, 1)))
            joint = joint[:, :, :, order]

            if self.mode == "train":
                joint = self._augment(joint)

            bone = compute_bone(joint)

            streams = torch.stack([
                joint,
                bone,
                compute_motion(joint, self._eff_fps, self.cfg.base_fps),
                compute_motion(bone,  self._eff_fps, self.cfg.base_fps),
                compute_angle(bone),
            ], dim=0)

            clips_out.append(torch.nan_to_num(streams, nan=0.0))

        if self.val_clips == 1:
            return clips_out[0], item["label"]

        return torch.stack(clips_out, dim=0), item["label"]