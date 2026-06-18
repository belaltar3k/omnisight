from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass
class FrameResult:
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class StreamingDetector(ABC):
    name: str = "base"
    modality: str = "video"

    @abstractmethod
    def load(self, device: str) -> None:
        """Load model weights onto the specified device."""

    @abstractmethod
    def process_frame(
        self, frame: np.ndarray, frame_idx: int, timestamp: float
    ) -> Optional[FrameResult]:
        """
        Process a single frame. Returns a FrameResult with anomaly score [0,1],
        or None if the detector is not ready to produce a score yet (e.g., buffer filling).
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state (e.g., on camera reconnect)."""

    def get_metadata(self) -> dict:
        """Return any current metadata from the detector."""
        return {}
