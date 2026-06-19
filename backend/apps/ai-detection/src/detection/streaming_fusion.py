from __future__ import annotations

import enum
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class AnomalyState(enum.Enum):
    NORMAL = "normal"
    WARMING = "warming"
    ANOMALOUS = "anomalous"
    COOLDOWN = "cooldown"


@dataclass
class AnomalyEvent:
    start_time: float
    end_time: Optional[float] = None
    peak_score: float = 0.0
    mean_score: float = 0.0
    component_peaks: dict[str, float] = field(default_factory=dict)


class StreamingFusionEngine:
    """
    Sliding-window fusion adapted from WeightedFusionEngine for real-time streaming.
    Maintains per-detector score histories and an anomaly state machine.
    """

    def __init__(
        self,
        weights: dict[str, float],
        anomaly_threshold: float = 0.55,
        smoothing_window: int = 5,
        dominance_weight: float = 0.85,
        min_anomaly_duration: float = 2.0,
        cooldown_duration: float = 3.0,
        history_size: int = 120,
        max_anomaly_duration: float = 30.0,
    ):
        self.weights = dict(weights)
        self.anomaly_threshold = anomaly_threshold
        self.smoothing_window = smoothing_window
        self.dominance_weight = dominance_weight
        self.min_anomaly_duration = min_anomaly_duration
        self.cooldown_duration = cooldown_duration
        self.max_anomaly_duration = max_anomaly_duration

        self._score_histories: dict[str, deque[float]] = {}
        self._history_size = history_size
        self._state = AnomalyState.NORMAL
        self._state_entered_at: float = 0.0
        self._current_event: Optional[AnomalyEvent] = None
        self._fused_score: float = 0.0
        self._score_accumulator: list[float] = []

    def update_weights(self, weights: dict[str, float]):
        self.weights = dict(weights)

    def _renormalize_weights(self, active_names: set[str]) -> dict[str, float]:
        filtered = {k: v for k, v in self.weights.items() if k in active_names and v > 0}
        total = sum(filtered.values())
        if total <= 0:
            return {k: 0.0 for k in filtered}
        return {k: v / total for k, v in filtered.items()}

    def push_score(self, detector_name: str, score: float):
        if detector_name not in self._score_histories:
            self._score_histories[detector_name] = deque(maxlen=self._history_size)
        self._score_histories[detector_name].append(score)

    def fuse(self) -> float:
        active = {
            name for name, history in self._score_histories.items()
            if len(history) > 0
        }
        active_weights = self._renormalize_weights(active)

        if not active_weights:
            self._fused_score = 0.0
            return 0.0

        weighted_sum = 0.0
        max_component = 0.0
        for name, weight in active_weights.items():
            history = self._score_histories.get(name)
            if history:
                score = history[-1]
                weighted_sum += weight * score
                max_component = max(max_component, score)

        fused = weighted_sum
        if self.dominance_weight > 0:
            fused = max(fused, max_component * self.dominance_weight)

        if len(self._score_accumulator) >= self.smoothing_window:
            self._score_accumulator = self._score_accumulator[-(self.smoothing_window - 1):]
        self._score_accumulator.append(fused)

        if len(self._score_accumulator) >= self.smoothing_window:
            fused = float(np.mean(self._score_accumulator[-self.smoothing_window:]))

        self._fused_score = max(0.0, min(1.0, fused))
        return self._fused_score

    def update_state(self, timestamp: float) -> tuple[AnomalyState, Optional[AnomalyEvent]]:
        """
        Advance the anomaly state machine. Returns the new state and
        an AnomalyEvent if an anomaly was just confirmed (WARMING -> ANOMALOUS).
        """
        score = self._fused_score
        event = None

        if self._state == AnomalyState.NORMAL:
            if score >= self.anomaly_threshold:
                self._state = AnomalyState.WARMING
                self._state_entered_at = timestamp
                self._current_event = AnomalyEvent(
                    start_time=timestamp, peak_score=score
                )

        elif self._state == AnomalyState.WARMING:
            if score < self.anomaly_threshold:
                self._state = AnomalyState.NORMAL
                self._current_event = None
            else:
                duration = timestamp - self._state_entered_at
                if self._current_event:
                    self._current_event.peak_score = max(self._current_event.peak_score, score)
                if duration >= self.min_anomaly_duration:
                    self._state = AnomalyState.ANOMALOUS
                    self._state_entered_at = timestamp
                    if self._current_event:
                        self._current_event.component_peaks = self._get_component_peaks()
                    event = self._current_event

        elif self._state == AnomalyState.ANOMALOUS:
            if self._current_event:
                self._current_event.peak_score = max(self._current_event.peak_score, score)
            duration = timestamp - self._state_entered_at
            if score < self.anomaly_threshold or duration >= self.max_anomaly_duration:
                if duration >= self.max_anomaly_duration:
                    logger.info(
                        "Anomaly timed out after %.1fs (score=%.3f) — forcing COOLDOWN",
                        duration, score,
                    )
                    # Flush the score accumulator so the smoothed score can decay
                    self._score_accumulator.clear()
                self._state = AnomalyState.COOLDOWN
                self._state_entered_at = timestamp

        elif self._state == AnomalyState.COOLDOWN:
            duration = timestamp - self._state_entered_at
            if duration >= self.cooldown_duration:
                if self._current_event:
                    self._current_event.end_time = timestamp
                self._state = AnomalyState.NORMAL
                self._current_event = None

        return self._state, event

    def _get_component_peaks(self) -> dict[str, float]:
        peaks = {}
        for name, history in self._score_histories.items():
            if history:
                peaks[name] = float(max(history))
        return peaks

    @property
    def fused_score(self) -> float:
        return self._fused_score

    @property
    def state(self) -> AnomalyState:
        return self._state

    @property
    def active_weights(self) -> dict[str, float]:
        active = {
            name for name, history in self._score_histories.items()
            if len(history) > 0
        }
        return self._renormalize_weights(active)

    def reset(self):
        self._score_histories.clear()
        self._state = AnomalyState.NORMAL
        self._current_event = None
        self._fused_score = 0.0
        self._score_accumulator.clear()
