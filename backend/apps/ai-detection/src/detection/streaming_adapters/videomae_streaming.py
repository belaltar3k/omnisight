from __future__ import annotations

import logging
from collections import deque
from typing import Optional

import numpy as np
import torch

from .base import FrameResult, StreamingDetector

logger = logging.getLogger(__name__)


class VideoMAEStreamingDetector(StreamingDetector):
    name = "video_mae"
    modality = "video"

    def __init__(
        self,
        weights_path: str,
        clip_len: int = 16,
        stride: int = 8,
        num_snippets: int = 32,
        infer_every_n_clips: int = 4,
    ):
        self.weights_path = weights_path
        self.clip_len = clip_len
        self.stride = stride
        self.num_snippets = num_snippets
        self.infer_every_n_clips = infer_every_n_clips
        self.device = "cpu"

        self.processor = None
        self.extractor = None
        self.model = None
        self.cfg = None
        self.pool_to_snippets = None
        self.CRIME_CLASSES = None

        self._frame_buffer: deque[np.ndarray] = deque(maxlen=clip_len)
        self._embedding_buffer: deque[np.ndarray] = deque(maxlen=128)
        self._frames_since_clip = 0
        self._clips_since_infer = 0
        self._last_score = 0.0
        self._last_crime_class = "Normal"

    def load(self, device: str) -> None:
        from transformers import VideoMAEImageProcessor, VideoMAEModel
        from components.video_mae.config import Config
        from components.video_mae.data import pool_to_snippets
        from components.video_mae.data.taxonomy import CRIME_CLASSES, NUM_CLASSES
        from components.video_mae.models import CrimeTransformer

        self.device = device
        self.cfg = Config()
        self.pool_to_snippets = pool_to_snippets
        self.CRIME_CLASSES = CRIME_CLASSES

        logger.info("Loading VideoMAE-Large feature extractor (fp16)")
        self.processor = VideoMAEImageProcessor.from_pretrained("MCG-NJU/videomae-large")
        self.extractor = VideoMAEModel.from_pretrained(
            "MCG-NJU/videomae-large",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        ).to(device).eval()

        logger.info("Loading CrimeTransformer from %s", self.weights_path)
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

    def process_frame(
        self, frame: np.ndarray, frame_idx: int, timestamp: float
    ) -> Optional[FrameResult]:
        if self.model is None:
            return None

        self._frame_buffer.append(frame)
        self._frames_since_clip += 1

        if self._frames_since_clip < self.stride or len(self._frame_buffer) < self.clip_len:
            if self._embedding_buffer:
                return FrameResult(
                    score=self._last_score,
                    metadata={"crime_class": self._last_crime_class},
                )
            return None

        self._frames_since_clip = 0
        clip_frames = list(self._frame_buffer)

        with torch.no_grad():
            emb = self._extract_embedding(clip_frames)
        self._embedding_buffer.append(emb)
        self._clips_since_infer += 1

        if (
            self._clips_since_infer >= self.infer_every_n_clips
            and len(self._embedding_buffer) >= self.num_snippets
        ):
            self._clips_since_infer = 0
            self._run_inference()

        return FrameResult(
            score=self._last_score,
            metadata={"crime_class": self._last_crime_class},
        )

    def _extract_embedding(self, clip_frames: list[np.ndarray]) -> np.ndarray:
        rgb_frames = [f[:, :, ::-1] for f in clip_frames]
        inputs = self.processor(rgb_frames, return_tensors="pt").pixel_values.to(
            self.device, dtype=torch.float16
        )
        emb = (
            self.extractor(inputs).last_hidden_state.mean(dim=1).float().cpu().numpy()
        )
        return emb.squeeze(0)

    def _run_inference(self):
        features = np.array(list(self._embedding_buffer))
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        features = features / (norms + 1e-6)
        features = self.pool_to_snippets(features, self.num_snippets)
        mags = np.linalg.norm(features, axis=1, keepdims=True).astype(np.float32)

        feat_tensor = torch.from_numpy(features).unsqueeze(0).to(self.device)
        mag_tensor = torch.from_numpy(mags).unsqueeze(0).to(self.device)

        with torch.no_grad():
            scores, logits = self.model(feat_tensor, mag_tensor)

        scores_np = scores.squeeze(0).cpu().numpy()
        probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

        self._last_score = float(scores_np.mean())
        self._last_crime_class = self.CRIME_CLASSES[int(probs.argmax())]

    def reset(self) -> None:
        self._frame_buffer.clear()
        self._embedding_buffer.clear()
        self._frames_since_clip = 0
        self._clips_since_infer = 0
        self._last_score = 0.0
        self._last_crime_class = "Normal"

    def get_metadata(self) -> dict:
        return {"crime_class": self._last_crime_class}
