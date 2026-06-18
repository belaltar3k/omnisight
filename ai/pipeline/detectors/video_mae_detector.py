from __future__ import annotations

from typing import Optional

import numpy as np
import torch
from decord import VideoReader, cpu
from transformers import VideoMAEImageProcessor, VideoMAEModel

from ..base import BaseDetector, DetectorResult


class VideoMAEDetector(BaseDetector):
    name = "video_mae"
    modality = "video"

    def __init__(self, weights_path: str) -> None:
        self.weights_path = weights_path
        self.device = "cpu"
        self.model = None
        self.processor = None
        self.extractor = None

    def load(self, device: str) -> None:
        import sys, os
        comp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        if comp_root not in sys.path:
            sys.path.insert(0, comp_root)

        from components.video_mae.config import Config
        from components.video_mae.data import pool_to_snippets
        from components.video_mae.data.taxonomy import CRIME_CLASSES, NUM_CLASSES
        from components.video_mae.models import CrimeTransformer

        self.device = device
        self.cfg = Config()
        self.pool_to_snippets = pool_to_snippets
        self.CRIME_CLASSES = CRIME_CLASSES

        print(f"[VideoMAE] Loading VideoMAE-Large feature extractor (fp16)...")
        self.processor = VideoMAEImageProcessor.from_pretrained("MCG-NJU/videomae-large")
        self.extractor = VideoMAEModel.from_pretrained(
            "MCG-NJU/videomae-large",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        ).to(device).eval()

        print(f"[VideoMAE] Loading CrimeTransformer from {self.weights_path}...")
        self.model = CrimeTransformer(
            feature_dim=self.cfg.feature_dim,
            num_classes=NUM_CLASSES,
            num_snippets=self.cfg.num_snippets,
            d_model=self.cfg.d_model,
            nhead=self.cfg.nhead,
            num_layers=self.cfg.num_layers,
            dropout=self.cfg.dropout,
        ).to(device)

        ckpt = torch.load(self.weights_path, map_location=device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state"])
        self.model.eval()

    def _process_clip_batch(self, clips: list) -> np.ndarray:
        try:
            inputs = self.processor(clips, return_tensors="pt").pixel_values.to(self.device, dtype=torch.float16)
            return self.extractor(inputs).last_hidden_state.mean(dim=1).float().cpu().numpy()
        except (ValueError, RuntimeError):
            embs = []
            for clip in clips:
                inp = self.processor([clip], return_tensors="pt").pixel_values.to(self.device, dtype=torch.float16)
                emb = self.extractor(inp).last_hidden_state.mean(dim=1).float().cpu().numpy()
                embs.append(emb)
            return np.vstack(embs)

    def predict(self, video_path: str, **kwargs) -> Optional[DetectorResult]:
        vr = VideoReader(video_path, ctx=cpu(0))
        total_frames = len(vr)
        fps = vr.get_avg_fps()

        clip_len = 16
        stride = 8
        batch_size = 32

        frame_indices = list(range(0, max(total_frames - clip_len + 1, 1), stride))
        if not frame_indices:
            frame_indices = [0]

        all_embs: list[np.ndarray] = []

        with torch.no_grad():
            for b_start in range(0, len(frame_indices), batch_size):
                batch_starts = frame_indices[b_start: b_start + batch_size]
                clips = []
                for s in batch_starts:
                    end = min(s + clip_len, total_frames)
                    idxs = list(range(s, end))
                    while len(idxs) < clip_len:
                        idxs.append(idxs[-1])
                    clip = vr.get_batch(idxs).asnumpy()
                    clips.append(list(clip))
                embs = self._process_clip_batch(clips)
                all_embs.append(embs)

        features = np.vstack(all_embs)

        norms = np.linalg.norm(features, axis=1, keepdims=True)
        features = features / (norms + 1e-6)
        features = self.pool_to_snippets(features, self.cfg.num_snippets)
        mags = np.linalg.norm(features, axis=1, keepdims=True).astype(np.float32)

        feat_tensor = torch.from_numpy(features).unsqueeze(0).to(self.device)
        mag_tensor = torch.from_numpy(mags).unsqueeze(0).to(self.device)

        with torch.no_grad():
            scores, logits = self.model(feat_tensor, mag_tensor)

        scores = scores.squeeze(0).cpu().numpy()
        probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

        if len(scores) >= 5:
            scores = np.convolve(scores, np.ones(5) / 5, mode="same")

        predicted_class = self.CRIME_CLASSES[int(probs.argmax())]

        frame_scores = np.interp(
            np.linspace(0, 1, total_frames),
            np.linspace(0, 1, len(scores)),
            scores,
        )

        return DetectorResult(
            scores=frame_scores.astype(np.float32),
            num_frames=total_frames,
            metadata={"crime_class": predicted_class, "class_probs": probs.tolist()},
        )
