from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class AnomalyRegion:
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    peak_score: float
    mean_score: float


@dataclass
class PipelineResult:
    fused_scores: np.ndarray
    anomaly_mask: np.ndarray
    anomaly_regions: list[AnomalyRegion]

    component_scores: dict[str, np.ndarray]
    component_metadata: dict[str, dict[str, Any]]
    active_weights: dict[str, float]

    num_frames: int
    fps: float
    duration: float
    threshold: float

    is_anomalous: bool
    peak_score: float
    processing_time: float

    failed_components: dict[str, str] = field(default_factory=dict)
    disabled_components: list[str] = field(default_factory=list)
