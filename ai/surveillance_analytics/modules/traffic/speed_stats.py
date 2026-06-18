from __future__ import annotations

import time
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class SpeedStatistics(ModuleBase):
    NAME = "speed_statistics"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._all_speeds: deque = deque(maxlen=5000)
        self._minute_series: list[dict] = []
        self._current_minute_speeds: list[float] = []
        self._last_minute_ts = time.time()
        self._speeding_count = 0
        self._total_measured = 0

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()
        vehicle_speeds: dict[int, float] = {}
        frame_speeds: list[float] = []

        for tid, track in tracks.items():
            if track.class_id not in VEHICLE_CLASS_IDS:
                continue
            if len(track.centroid_history) < 3:
                continue

            speed_kmh = track.speed_kmh
            vehicle_speeds[tid] = speed_kmh

            if speed_kmh > 2.0:
                frame_speeds.append(speed_kmh)
                self._all_speeds.append(speed_kmh)
                self._current_minute_speeds.append(speed_kmh)
                self._total_measured += 1
                if speed_kmh > self.config.speed_limit_kmh:
                    self._speeding_count += 1

        # Minute aggregation
        if now - self._last_minute_ts >= 60:
            if self._current_minute_speeds:
                arr = np.array(self._current_minute_speeds)
                self._minute_series.append({
                    "timestamp": now,
                    "mean": round(float(np.mean(arr)), 1),
                    "median": round(float(np.median(arr)), 1),
                    "p90": round(float(np.percentile(arr, 90)), 1),
                    "max": round(float(np.max(arr)), 1),
                    "count": len(arr),
                })
            if len(self._minute_series) > 120:
                self._minute_series = self._minute_series[-120:]
            self._current_minute_speeds = []
            self._last_minute_ts = now

        # Compute overall stats
        stats: dict = {"vehicle_speeds": vehicle_speeds, "current_count": len(vehicle_speeds)}

        if self._all_speeds:
            arr = np.array(list(self._all_speeds))
            stats.update({
                "mean_speed": round(float(np.mean(arr)), 1),
                "median_speed": round(float(np.median(arr)), 1),
                "p25_speed": round(float(np.percentile(arr, 25)), 1),
                "p75_speed": round(float(np.percentile(arr, 75)), 1),
                "p90_speed": round(float(np.percentile(arr, 90)), 1),
                "p99_speed": round(float(np.percentile(arr, 99)), 1),
                "max_speed": round(float(np.max(arr)), 1),
                "min_speed": round(float(np.min(arr)), 1),
                "std_speed": round(float(np.std(arr)), 1),
                "speed_limit": self.config.speed_limit_kmh,
                "speeding_rate": round(self._speeding_count / max(self._total_measured, 1), 4),
                "total_measured": self._total_measured,
                "speeding_count": self._speeding_count,
            })

            # Histogram bins
            bins = [0, 10, 20, 30, 40, 50, 60, 80, 100, 150]
            hist, _ = np.histogram(arr, bins=bins)
            stats["speed_histogram"] = {f"{bins[i]}-{bins[i+1]}": int(hist[i]) for i in range(len(hist))}
        else:
            stats.update({"mean_speed": 0, "median_speed": 0, "speeding_rate": 0})

        stats["minute_series"] = self._minute_series[-10:]

        if stats.get("speeding_rate", 0) > 0.3:
            self._alerts.append({
                "type": "high_speeding_rate",
                "message": f"High speeding rate: {stats['speeding_rate']:.0%} of vehicles exceed {self.config.speed_limit_kmh} km/h",
                "severity": "warning",
                "confidence": stats["speeding_rate"],
                "metadata": {"speeding_rate": stats["speeding_rate"], "mean_speed": stats["mean_speed"]},
            })

        self._display_data = stats
        return stats
