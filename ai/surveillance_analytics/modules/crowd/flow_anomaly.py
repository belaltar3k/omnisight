from __future__ import annotations

from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class FlowAnomalyIndex(ModuleBase):
    NAME = "flow_anomaly_index"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._prev_gray: np.ndarray | None = None
        self._baseline_magnitudes: deque = deque(maxlen=500)
        self._baseline_consistencies: deque = deque(maxlen=500)
        self._minute_series: deque = deque(maxlen=60)
        self._last_minute_ts = 0.0
        self._current_minute_scores: list[float] = []
        self._anomaly_count = 0
        self._total_samples = 0

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        import time
        now = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self._prev_gray is None:
            self._prev_gray = gray
            return {"flow_magnitude": 0, "anomaly_score": 0, "deviation_sigma": 0}

        flow = cv2.calcOpticalFlowFarneback(
            self._prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
        )
        self._prev_gray = gray

        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        avg_mag = float(np.mean(magnitude))

        dx_mean = float(np.mean(flow[..., 0]))
        dy_mean = float(np.mean(flow[..., 1]))
        mean_vec_mag = np.sqrt(dx_mean ** 2 + dy_mean ** 2)
        consistency = min(mean_vec_mag / max(avg_mag, 1e-6), 1.0)

        self._baseline_magnitudes.append(avg_mag)
        self._baseline_consistencies.append(consistency)
        self._total_samples += 1

        baseline_mean = float(np.mean(list(self._baseline_magnitudes)))
        baseline_std = float(np.std(list(self._baseline_magnitudes))) + 1e-6
        deviation = (avg_mag - baseline_mean) / baseline_std

        anomaly_score = max(0.0, min(deviation / 5.0 * consistency, 1.0))
        is_anomaly = deviation > 3.0 and consistency > self.config.panic_flow_thresh

        if is_anomaly:
            self._anomaly_count += 1

        self._current_minute_scores.append(anomaly_score)

        if now - self._last_minute_ts >= 60:
            if self._current_minute_scores:
                self._minute_series.append({
                    "timestamp": now,
                    "avg_score": round(float(np.mean(self._current_minute_scores)), 3),
                    "max_score": round(float(np.max(self._current_minute_scores)), 3),
                    "avg_magnitude": round(baseline_mean, 3),
                })
            self._current_minute_scores = []
            self._last_minute_ts = now

        avg_consistency = float(np.mean(list(self._baseline_consistencies))) if self._baseline_consistencies else 0

        stats = {
            "flow_magnitude": round(avg_mag, 3),
            "flow_consistency": round(consistency, 3),
            "avg_consistency": round(avg_consistency, 3),
            "deviation_sigma": round(deviation, 2),
            "anomaly_score": round(anomaly_score, 3),
            "is_anomaly": is_anomaly,
            "baseline_mean": round(baseline_mean, 3),
            "baseline_std": round(baseline_std, 3),
            "anomaly_count": self._anomaly_count,
            "anomaly_rate": round(self._anomaly_count / max(self._total_samples, 1), 4),
            "total_samples": self._total_samples,
            "minute_series": list(self._minute_series)[-10:],
        }

        if is_anomaly:
            self._alerts.append({
                "type": "flow_anomaly",
                "message": f"Unusual crowd flow detected (deviation {deviation:.1f}σ, consistency {consistency:.2f})",
                "severity": "info",
                "confidence": anomaly_score,
                "metadata": {"deviation": round(deviation, 2), "consistency": round(consistency, 3)},
            })

        self._display_data = stats
        return stats
