from __future__ import annotations

import cv2
import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class ActivityHeatmap(ModuleBase):
    NAME = "activity_heatmap"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._heatmap = np.zeros(
            (config.process_height, config.process_width), dtype=np.float32
        )
        self._decay = 0.997
        self._sigma = 20
        self._frame_count = 0

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        self._heatmap *= self._decay

        for tid, track in tracks.items():
            if track.class_id == PERSON_CLASS_ID:
                cx, cy = track.centroid
                h, w = self._heatmap.shape
                y_lo = max(0, cy - 50)
                y_hi = min(h, cy + 50)
                x_lo = max(0, cx - 50)
                x_hi = min(w, cx + 50)

                if y_hi > y_lo and x_hi > x_lo:
                    y_coords = np.arange(y_lo, y_hi).reshape(-1, 1)
                    x_coords = np.arange(x_lo, x_hi).reshape(1, -1)
                    blob = np.exp(
                        -((x_coords - cx) ** 2 + (y_coords - cy) ** 2) / (2 * self._sigma ** 2)
                    ).astype(np.float32)
                    self._heatmap[y_lo:y_hi, x_lo:x_hi] += blob

        heatmap_overlay = None
        peak = float(self._heatmap.max())
        if peak > 0.1:
            normalized = np.clip(self._heatmap / max(peak, 1.0) * 255, 0, 255).astype(np.uint8)
            heatmap_overlay = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

        self._display_data = {"heatmap_overlay": heatmap_overlay}
        self._frame_count += 1

        return {"peak_density": peak, "heatmap_overlay": heatmap_overlay}
