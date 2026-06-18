from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass
class DetectorResult:
    """Standardised output from any anomaly detector."""

    scores: np.ndarray
    """Per-frame (or per-segment) anomaly scores in [0, 1]."""

    num_frames: int
    """Total frames in the source video (used for alignment)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Component-specific extras (crime_class, weapon_boxes, events, etc.)."""


class BaseDetector(ABC):
    """Interface every anomaly-detection component must implement."""

    name: str = "base"
    modality: str = "video"  # "video" | "audio" | "frame"

    @abstractmethod
    def load(self, device: str) -> None:
        """Load model weights and prepare for inference."""

    @abstractmethod
    def predict(self, video_path: str, **kwargs) -> Optional[DetectorResult]:
        """
        Run inference on a video file.

        Returns None when the detector cannot run (e.g., no audio track for PAAN).
        """
