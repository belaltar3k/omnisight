"""
UCF-Crime dataset with fixed 32-snippet temporal pooling.

Each sample is pooled from variable-length VideoMAE features into a
fixed-length representation, matching the RTFM / MGFN paradigm.
"""

import glob
import os
import random

import numpy as np
import torch
from torch.utils.data import Dataset

from .taxonomy import CRIME_CLASSES, NUM_CLASSES, class_index_from_path


# ── Temporal pooling ─────────────────────────────────────────────────────────

def pool_to_snippets(features: np.ndarray, num_snippets: int) -> np.ndarray:
    """
    Temporally pool variable-length features into exactly num_snippets.

    Each output snippet is the mean of the source clips assigned to it,
    which is the standard approach in RTFM, MGFN, and related SOTA methods.

    Args:
        features:     (N, D) float32 array of per-clip features.
        num_snippets: target temporal resolution.

    Returns:
        (num_snippets, D) float32 array.
    """
    N = len(features)
    if N == 0:
        return np.zeros((num_snippets, features.shape[1]), dtype=np.float32)

    indices  = np.linspace(0, N, num_snippets + 1).astype(int)
    snippets = []

    for i in range(num_snippets):
        start, end = indices[i], indices[i + 1]
        if start >= end:
            snippet = features[start] if start < N else np.zeros(features.shape[1])
        else:
            snippet = features[start:end].mean(axis=0)
        snippets.append(snippet)

    return np.stack(snippets).astype(np.float32)


# ── Dataset ───────────────────────────────────────────────────────────────────

class UCFCrimeDataset(Dataset):
    """
    Loads pre-extracted VideoMAE features (.npy) for UCF-Crime.

    Directory layout expected:
        feature_dir/
            train/
                normal/   *.npy  (+ *_meta.npy)
                anomaly/
                    Abuse/    *.npy
                    Robbery/  *.npy
                    …
            test/
                …  (same structure)

    Each sample dict contains:
        features    (num_snippets, feature_dim)  — L2-normalised, pooled
        magnitudes  (num_snippets, 1)            — post-pool L2 norms
        clip_labels (num_snippets,)              — binary anomaly labels
        video_label float                        — 0 normal / 1 anomaly
        crime_class long                         — fine-grained class index
    """

    def __init__(
        self,
        feature_dir: str,
        split: str = "train",
        annotations: dict | None = None,
        num_snippets: int = 32,
        is_train: bool = True,
    ):
        self.num_snippets = num_snippets
        self.annotations  = annotations or {}
        self.is_train     = is_train
        self.samples: list[tuple[str, str, int, int]] = []

        split_dir = os.path.join(feature_dir, split)

        # ── Normal videos ────────────────────────────────────────
        normal_dir = os.path.join(split_dir, "normal")
        for fp in glob.glob(os.path.join(normal_dir, "*.npy")):
            if "_meta" not in fp:
                self.samples.append((fp, fp.replace(".npy", "_meta.npy"), 0, 0))

        # ── Anomaly videos ───────────────────────────────────────
        anomaly_dir = os.path.join(split_dir, "anomaly")
        if os.path.exists(anomaly_dir):
            for fp in glob.glob(os.path.join(anomaly_dir, "**", "*.npy"), recursive=True):
                if "_meta" not in fp:
                    crime_class = class_index_from_path(fp)
                    self.samples.append((fp, fp.replace(".npy", "_meta.npy"), 1, crime_class))

        n_normal  = sum(1 for s in self.samples if s[2] == 0)
        n_anomaly = sum(1 for s in self.samples if s[2] == 1)
        print(
            f"[{split:5s}] {len(self.samples)} videos — "
            f"{n_normal} normal | {n_anomaly} anomaly"
        )

    def __len__(self) -> int:
        return len(self.samples)

    # ── Internal helpers ─────────────────────────────────────────

    def _load_meta(self, meta_path: str) -> tuple[list, float]:
        """Load clip timestamps and FPS from a _meta.npy sidecar file."""
        timestamps, fps = [], 30.0
        if os.path.exists(meta_path):
            try:
                meta       = np.load(meta_path, allow_pickle=True).item()
                timestamps = meta.get("clip_timestamps_sec", [])
                fps        = float(meta.get("fps", 30.0)) or 30.0
            except Exception:
                pass
        return timestamps, fps

    def _build_clip_labels(
        self,
        feat_path: str,
        num_clips: int,
        timestamps: list,
        fps: float,
        video_label: int,
    ) -> np.ndarray:
        """
        Assign per-clip binary labels.

        Train: all clips in an anomaly video are labelled 1 — the MIL
        loss then learns to find the truly anomalous ones.
        Test:  use precise temporal annotations when available.
        """
        labels = np.zeros(num_clips, dtype=np.float32)
        if video_label == 0:
            return labels

        if self.is_train:
            labels[:] = 1.0
            return labels

        # Test — use frame-level annotations
        stem = os.path.splitext(os.path.basename(feat_path))[0]
        if stem in self.annotations and len(timestamps) > 0:
            for sf, ef in self.annotations[stem]:
                start_sec = sf / fps
                end_sec   = ef / fps
                for i, ts in enumerate(timestamps[:num_clips]):
                    if start_sec <= ts <= end_sec:
                        labels[i] = 1.0
            if labels.sum() == 0:
                labels[:] = 1.0   # fallback: whole video is anomaly
        else:
            labels[:] = 1.0

        return labels

    def _augment(self, features: np.ndarray) -> np.ndarray:
        """Light training augmentation: Gaussian noise + snippet dropout."""
        features = features + np.random.normal(0, 0.01, features.shape).astype(np.float32)
        if random.random() < 0.5:
            n_drop   = max(1, self.num_snippets // 10)
            drop_idx = random.sample(range(self.num_snippets), k=n_drop)
            features[drop_idx] = 0.0
        return features

    # ── Public interface ─────────────────────────────────────────

    def get_sample_weights(self) -> list[float]:
        """2× weight for anomaly videos to counteract class imbalance."""
        return [2.0 if s[2] == 1 else 1.0 for s in self.samples]

    def __getitem__(self, idx: int) -> dict:
        feat_path, meta_path, video_label, crime_class = self.samples[idx]

        # Load + L2-normalise raw features
        features = np.load(feat_path).astype(np.float32)
        norms    = np.linalg.norm(features, axis=1, keepdims=True)
        features = features / (norms + 1e-6)

        timestamps, fps = self._load_meta(meta_path)
        num_clips       = features.shape[0]

        # Build clip labels BEFORE pooling (needed for test evaluation)
        clip_labels = self._build_clip_labels(
            feat_path, num_clips, timestamps, fps, video_label
        )

        # Pool to fixed num_snippets
        features    = pool_to_snippets(features, self.num_snippets)
        clip_labels = pool_to_snippets(
            clip_labels.reshape(-1, 1), self.num_snippets
        ).squeeze(-1)
        clip_labels = (clip_labels >= 0.5).astype(np.float32)

        if self.is_train:
            features = self._augment(features)

        # Magnitude as auxiliary signal (anomalous regions → higher magnitude)
        magnitudes = np.linalg.norm(features, axis=1, keepdims=True).astype(np.float32)

        return {
            "features":    torch.from_numpy(features),                          # (T, D)
            "magnitudes":  torch.from_numpy(magnitudes),                        # (T, 1)
            "clip_labels": torch.from_numpy(clip_labels),                       # (T,)
            "video_label": torch.tensor(video_label, dtype=torch.float32),
            "crime_class": torch.tensor(crime_class,  dtype=torch.long),
        }