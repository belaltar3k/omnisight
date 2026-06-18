from __future__ import annotations

from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class SceneBaseline(ModuleBase):
    NAME = "scene_baseline"
    TIER = "background"

    def __init__(self, config):
        super().__init__(config)
        self._reference_gray: np.ndarray | None = None
        self._reference_hist: np.ndarray | None = None
        self._stability_scores: deque = deque(maxlen=100)
        self._brightness_series: deque = deque(maxlen=500)
        self._change_events = 0
        self._total_checks = 0
        self._significant_change_threshold = 0.15

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.GaussianBlur(gray, (11, 11), 0)

        brightness = float(np.mean(gray))
        self._brightness_series.append(brightness)

        hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten()
        hist = hist / (hist.sum() + 1e-6)

        if self._reference_gray is None:
            self._reference_gray = gray_blur.copy()
            self._reference_hist = hist.copy()
            return {"stability_index": 1.0, "brightness": round(brightness, 1)}

        # Structural similarity via normalized correlation
        diff = cv2.absdiff(gray_blur, self._reference_gray)
        change_ratio = float((diff > 30).sum()) / max(diff.size, 1)

        # Histogram correlation
        hist_corr = float(cv2.compareHist(
            hist.astype(np.float32),
            self._reference_hist.astype(np.float32),
            cv2.HISTCMP_CORREL,
        ))

        stability_index = max(0.0, min(1.0 - change_ratio, 1.0))
        self._stability_scores.append(stability_index)
        self._total_checks += 1

        significant_change = change_ratio > self._significant_change_threshold
        if significant_change:
            self._change_events += 1

        avg_stability = float(np.mean(list(self._stability_scores))) if self._stability_scores else 1.0
        brightness_list = list(self._brightness_series)
        brightness_std = float(np.std(brightness_list)) if len(brightness_list) > 5 else 0

        # Visibility estimate: low brightness or high variance = poor visibility
        if brightness < 40:
            visibility = "very_low"
        elif brightness < 80:
            visibility = "low"
        elif brightness > 220:
            visibility = "overexposed"
        else:
            visibility = "good"

        stats = {
            "stability_index": round(stability_index, 3),
            "avg_stability": round(avg_stability, 3),
            "scene_change_ratio": round(change_ratio, 4),
            "histogram_correlation": round(hist_corr, 3),
            "brightness": round(brightness, 1),
            "brightness_std": round(brightness_std, 1),
            "visibility": visibility,
            "significant_changes": self._change_events,
            "change_rate": round(self._change_events / max(self._total_checks, 1), 3),
            "total_checks": self._total_checks,
        }

        if significant_change:
            self._alerts.append({
                "type": "scene_change",
                "message": f"Significant scene change detected (change ratio: {change_ratio:.1%})",
                "severity": "info",
                "confidence": min(change_ratio * 3, 1.0),
                "metadata": {"change_ratio": round(change_ratio, 4)},
            })

        self._display_data = stats
        return stats
