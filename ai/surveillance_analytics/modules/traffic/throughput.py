from __future__ import annotations

import time
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase

VEHICLE_TYPE_MAP = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


class TrafficThroughput(ModuleBase):
    NAME = "traffic_throughput"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._seen_ids: set[int] = set()
        self._counts_per_minute: deque = deque(maxlen=120)
        self._current_minute_count = 0
        self._current_minute_by_type: dict[str, int] = {}
        self._last_minute_ts = time.time()
        self._total_vehicles = 0
        self._type_totals: dict[str, int] = {}
        self._hourly_counts: list[dict] = []

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()

        for tid, track in tracks.items():
            if track.class_id not in VEHICLE_CLASS_IDS:
                continue
            if tid not in self._seen_ids:
                self._seen_ids.add(tid)
                self._total_vehicles += 1
                self._current_minute_count += 1

                vtype = VEHICLE_TYPE_MAP.get(track.class_id, "other")
                self._current_minute_by_type[vtype] = self._current_minute_by_type.get(vtype, 0) + 1
                self._type_totals[vtype] = self._type_totals.get(vtype, 0) + 1

        # Minute rollover
        if now - self._last_minute_ts >= 60:
            self._counts_per_minute.append({
                "timestamp": now,
                "count": self._current_minute_count,
                "by_type": dict(self._current_minute_by_type),
            })
            self._current_minute_count = 0
            self._current_minute_by_type = {}
            self._last_minute_ts = now

        # Compute rates
        minute_counts = [m["count"] for m in self._counts_per_minute]
        vehicles_per_minute = np.mean(minute_counts) if minute_counts else 0
        vehicles_per_hour = vehicles_per_minute * 60
        peak_minute = max(minute_counts) if minute_counts else 0

        current_in_frame = sum(1 for t in tracks.values() if t.class_id in VEHICLE_CLASS_IDS)

        stats = {
            "total_unique_vehicles": self._total_vehicles,
            "current_in_frame": current_in_frame,
            "vehicles_per_minute_avg": round(float(vehicles_per_minute), 2),
            "vehicles_per_hour_est": round(float(vehicles_per_hour), 0),
            "peak_per_minute": peak_minute,
            "type_breakdown": dict(self._type_totals),
            "type_percentages": {
                k: round(v / max(self._total_vehicles, 1) * 100, 1)
                for k, v in self._type_totals.items()
            },
            "minute_series": [
                {"ts": m["timestamp"], "count": m["count"]}
                for m in list(self._counts_per_minute)[-15:]
            ],
        }

        self._display_data = stats
        return stats
