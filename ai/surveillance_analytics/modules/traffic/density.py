from __future__ import annotations

import time
from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class TrafficDensity(ModuleBase):
    NAME = "traffic_density"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._road_poly = np.array(config.zones.get("road", []), dtype=np.int32)
        self._max_capacity = 15
        self._frame_counts: deque = deque(maxlen=900)
        self._minute_series: deque = deque(maxlen=120)
        self._current_minute_counts: list[int] = []
        self._last_minute_ts = time.time()
        self._time_above_jam = 0.0
        self._total_time = 0.0
        self._last_frame_ts = time.time()
        self._peak_count = 0

    def _in_zone(self, cx: int, cy: int) -> bool:
        if len(self._road_poly) < 3:
            return True
        return cv2.pointPolygonTest(self._road_poly, (float(cx), float(cy)), False) >= 0

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()
        dt = now - self._last_frame_ts
        self._last_frame_ts = now

        count = 0
        for tid, track in tracks.items():
            if track.class_id in VEHICLE_CLASS_IDS:
                if self._in_zone(track.centroid[0], track.centroid[1]):
                    count += 1

        self._frame_counts.append(count)
        self._current_minute_counts.append(count)
        self._peak_count = max(self._peak_count, count)

        congestion_index = min(count / max(self._max_capacity, 1), 1.0)
        is_jam = congestion_index > 0.8

        self._total_time += dt
        if is_jam:
            self._time_above_jam += dt

        # Minute aggregation
        if now - self._last_minute_ts >= 60:
            if self._current_minute_counts:
                arr = np.array(self._current_minute_counts)
                self._minute_series.append({
                    "timestamp": now,
                    "mean": round(float(np.mean(arr)), 1),
                    "max": int(np.max(arr)),
                    "congestion_index": round(float(np.mean(arr)) / max(self._max_capacity, 1), 2),
                })
            self._current_minute_counts = []
            self._last_minute_ts = now

        rolling_avg = float(np.mean(list(self._frame_counts))) if self._frame_counts else 0
        jam_time_pct = self._time_above_jam / max(self._total_time, 1) * 100

        stats = {
            "current_count": count,
            "rolling_avg_30s": round(rolling_avg, 1),
            "congestion_index": round(congestion_index, 2),
            "is_jam": is_jam,
            "peak_count": self._peak_count,
            "road_capacity": self._max_capacity,
            "utilization_pct": round(congestion_index * 100, 1),
            "jam_time_pct": round(jam_time_pct, 1),
            "total_observation_sec": round(self._total_time, 0),
            "minute_series": list(self._minute_series)[-10:],
        }

        if is_jam:
            self._alerts.append({
                "type": "congestion",
                "message": f"Road congestion: {count} vehicles (index {congestion_index:.2f})",
                "severity": "warning",
                "confidence": congestion_index,
                "metadata": {"count": count, "congestion_index": round(congestion_index, 2)},
            })

        self._display_data = stats
        return stats
