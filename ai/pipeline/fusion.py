from __future__ import annotations

import numpy as np

from .base import DetectorResult
from .result import AnomalyRegion, PipelineResult


class WeightedFusionEngine:

    def __init__(
        self,
        weights: dict[str, float],
        anomaly_threshold: float = 0.55,
        smoothing_window: int = 5,
        dominance_weight: float = 0.0,
    ) -> None:
        self.weights = weights
        self.anomaly_threshold = anomaly_threshold
        self.smoothing_window = smoothing_window
        self.dominance_weight = dominance_weight

    def fuse(
        self,
        results: dict[str, DetectorResult],
        num_frames: int,
        fps: float,
        *,
        processing_time: float = 0.0,
        failed_components: dict[str, str] | None = None,
        disabled_components: list[str] | None = None,
    ) -> PipelineResult:
        active_weights = self._renormalize_weights(set(results.keys()))

        if not active_weights:
            zeros = np.zeros(num_frames, dtype=np.float32)
            return PipelineResult(
                fused_scores=zeros,
                anomaly_mask=np.zeros(num_frames, dtype=bool),
                anomaly_regions=[],
                component_scores={},
                component_metadata={},
                active_weights={},
                num_frames=num_frames,
                fps=fps,
                duration=num_frames / fps if fps > 0 else 0.0,
                threshold=self.anomaly_threshold,
                is_anomalous=False,
                peak_score=0.0,
                processing_time=processing_time,
                failed_components=failed_components or {},
                disabled_components=disabled_components or [],
            )

        component_scores: dict[str, np.ndarray] = {}
        component_metadata: dict[str, dict] = {}

        fused = np.zeros(num_frames, dtype=np.float64)
        all_aligned: list[np.ndarray] = []
        for name, weight in active_weights.items():
            aligned = self._align_scores(results[name].scores, num_frames)
            component_scores[name] = aligned
            component_metadata[name] = results[name].metadata
            fused += weight * aligned
            all_aligned.append(aligned)

        if self.dominance_weight > 0 and all_aligned:
            max_component = np.maximum.reduce(all_aligned)
            fused = np.maximum(fused, max_component * self.dominance_weight)

        fused = self._smooth(fused).astype(np.float32)
        fused = np.clip(fused, 0.0, 1.0)

        anomaly_mask = fused >= self.anomaly_threshold
        anomaly_regions = self._extract_anomaly_regions(fused, anomaly_mask, fps)

        return PipelineResult(
            fused_scores=fused,
            anomaly_mask=anomaly_mask,
            anomaly_regions=anomaly_regions,
            component_scores=component_scores,
            component_metadata=component_metadata,
            active_weights=active_weights,
            num_frames=num_frames,
            fps=fps,
            duration=num_frames / fps if fps > 0 else 0.0,
            threshold=self.anomaly_threshold,
            is_anomalous=bool(anomaly_mask.any()),
            peak_score=float(fused.max()) if num_frames > 0 else 0.0,
            processing_time=processing_time,
            failed_components=failed_components or {},
            disabled_components=disabled_components or [],
        )

    def _renormalize_weights(self, active_names: set[str]) -> dict[str, float]:
        filtered = {k: v for k, v in self.weights.items() if k in active_names and v >= 0}
        total = sum(filtered.values())
        if total <= 0:
            return {k: 0.0 for k in filtered.keys()}
        return {k: v / total for k, v in filtered.items()}

    @staticmethod
    def _align_scores(scores: np.ndarray, target_length: int) -> np.ndarray:
        if len(scores) == target_length:
            return scores.astype(np.float64)
        if len(scores) == 0:
            return np.zeros(target_length, dtype=np.float64)
        if len(scores) == 1:
            return np.full(target_length, scores[0], dtype=np.float64)
        return np.interp(
            np.linspace(0, 1, target_length),
            np.linspace(0, 1, len(scores)),
            scores,
        ).astype(np.float64)

    def _smooth(self, scores: np.ndarray) -> np.ndarray:
        if self.smoothing_window <= 1 or len(scores) < self.smoothing_window:
            return scores
        kernel = np.ones(self.smoothing_window) / self.smoothing_window
        return np.convolve(scores, kernel, mode="same")

    @staticmethod
    def _extract_anomaly_regions(
        scores: np.ndarray, mask: np.ndarray, fps: float,
    ) -> list[AnomalyRegion]:
        if not mask.any():
            return []

        padded = np.concatenate(([False], mask, [False]))
        edges = np.diff(padded.astype(np.int8))
        starts = np.where(edges == 1)[0]
        ends = np.where(edges == -1)[0]

        regions: list[AnomalyRegion] = []
        for s, e in zip(starts, ends):
            segment = scores[s:e]
            regions.append(AnomalyRegion(
                start_frame=int(s),
                end_frame=int(e),
                start_time=s / fps if fps > 0 else 0.0,
                end_time=e / fps if fps > 0 else 0.0,
                peak_score=float(segment.max()),
                mean_score=float(segment.mean()),
            ))
        return regions
