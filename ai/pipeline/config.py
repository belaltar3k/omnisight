from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineConfig:
    # -- Component weights (re-normalised at runtime if a component is unavailable) --
    weights: dict[str, float] = field(default_factory=lambda: {
        "crime_skelnet": 0.45,
        "paan": 0.25,
        "weapon_detection": 0.25,
        "video_mae": 0.05,
        "surveillance_analytics": 0.0,
    })

    # -- Decision threshold --
    anomaly_threshold: float = 0.55

    # -- Model paths --
    video_mae_weights: str = ""
    skelnet_weights: str = ""
    weapon_weights: str = ""

    # -- Processing --
    device: str = "cuda"
    weapon_sample_fps: int = 2
    smoothing_window: int = 5

    # -- Fusion: if any single component score exceeds the threshold on its own
    #    (scaled by this factor), the fused score reflects that instead of being
    #    diluted by components that don't cover this crime type.
    #    fused[i] = max(weighted_avg[i], max_component[i] * dominance_weight)
    dominance_weight: float = 0.85

    # -- Tracker (YOLO-pose) --
    pose_model: str = ""

    # -- Disabled components (pass names to skip) --
    disabled: list[str] = field(default_factory=list)
