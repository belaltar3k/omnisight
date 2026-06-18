from __future__ import annotations

import time
from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class CrowdDensity(ModuleBase):
    NAME = "crowd_density"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._frame_counts: deque = deque(maxlen=900)
        self._minute_series: deque = deque(maxlen=120)
        self._current_minute_counts: list[int] = []
        self._last_minute_ts = time.time()
        self._total_unique: set[int] = set()
        self._peak_count = 0
        self._zone_counts: dict[str, deque] = {}
        for zone_name in config.zones:
            self._zone_counts[zone_name] = deque(maxlen=300)

    def _get_zone(self, cx: int, cy: int) -> str | None:
        for zone_name, pts in self.config.zones.items():
            if len(pts) < 3:
                continue
            poly = np.array(pts, dtype=np.int32)
            if cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0:
                return zone_name
        return None

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()

        count = sum(1 for d in detections if d["class_id"] == PERSON_CLASS_ID)
        self._frame_counts.append(count)
        self._current_minute_counts.append(count)
        self._peak_count = max(self._peak_count, count)

        # Track unique persons
        for tid, track in tracks.items():
            if track.class_id == PERSON_CLASS_ID:
                self._total_unique.add(tid)

        # Per-zone density
        zone_current: dict[str, int] = {z: 0 for z in self.config.zones}
        for tid, track in tracks.items():
            if track.class_id != PERSON_CLASS_ID:
                continue
            zone = self._get_zone(track.centroid[0], track.centroid[1])
            if zone:
                zone_current[zone] += 1

        for zone_name, cnt in zone_current.items():
            if zone_name in self._zone_counts:
                self._zone_counts[zone_name].append(cnt)

        # Minute aggregation
        if now - self._last_minute_ts >= 60:
            if self._current_minute_counts:
                arr = np.array(self._current_minute_counts)
                self._minute_series.append({
                    "timestamp": now,
                    "mean": round(float(np.mean(arr)), 1),
                    "max": int(np.max(arr)),
                    "min": int(np.min(arr)),
                })
            self._current_minute_counts = []
            self._last_minute_ts = now

        rolling_avg = float(np.mean(list(self._frame_counts))) if self._frame_counts else 0
        capacity_util = count / max(self.config.crowd_max_capacity, 1)

        # Trend: compare last 30s average vs previous 30s
        counts_list = list(self._frame_counts)
        half = len(counts_list) // 2
        if half > 10:
            recent_avg = np.mean(counts_list[half:])
            older_avg = np.mean(counts_list[:half])
            if older_avg > 0:
                trend_pct = (recent_avg - older_avg) / older_avg * 100
            else:
                trend_pct = 0
        else:
            trend_pct = 0

        # Zone averages
        zone_avgs = {}
        for zone_name, q in self._zone_counts.items():
            if q:
                zone_avgs[zone_name] = round(float(np.mean(list(q))), 1)

        stats = {
            "current_count": count,
            "rolling_avg": round(rolling_avg, 1),
            "peak_count": self._peak_count,
            "total_unique_persons": len(self._total_unique),
            "capacity": self.config.crowd_max_capacity,
            "capacity_utilization_pct": round(capacity_util * 100, 1),
            "trend_pct": round(trend_pct, 1),
            "trend_direction": "increasing" if trend_pct > 5 else ("decreasing" if trend_pct < -5 else "stable"),
            "zone_current": zone_current,
            "zone_averages": zone_avgs,
            "minute_series": list(self._minute_series)[-10:],
        }

        if count > self.config.crowd_max_capacity:
            self._alerts.append({
                "type": "crowd_over_capacity",
                "message": f"Crowd count {count} exceeds capacity {self.config.crowd_max_capacity} ({capacity_util:.0%})",
                "severity": "warning",
                "confidence": min(capacity_util, 1.0),
                "metadata": {"count": count, "utilization": round(capacity_util, 2)},
            })

        self._display_data = stats
        return stats
