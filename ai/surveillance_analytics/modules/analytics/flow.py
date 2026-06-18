from __future__ import annotations

import time

import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


def _crosses_line(prev: tuple, curr: tuple, p1: tuple, p2: tuple) -> int:
    def cross_product(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = cross_product(p1, p2, prev)
    d2 = cross_product(p1, p2, curr)

    if d1 * d2 < 0:
        d3 = cross_product(prev, curr, p1)
        d4 = cross_product(prev, curr, p2)
        if d3 * d4 < 0:
            return 1 if d1 < 0 else -1
    return 0


class PedestrianFlow(ModuleBase):
    NAME = "pedestrian_flow"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._line_counts: dict[str, dict[str, int]] = {}
        self._prev_centroids: dict[int, tuple] = {}
        self._time_series: dict[str, list[dict]] = {}
        self._last_minute_ts = time.time()

        for line in config.counting_lines:
            name = line["name"]
            self._line_counts[name] = {"in": 0, "out": 0}
            self._time_series[name] = []

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()

        for tid, track in tracks.items():
            if track.class_id != PERSON_CLASS_ID:
                continue

            curr = track.centroid
            prev = self._prev_centroids.get(tid)
            self._prev_centroids[tid] = curr

            if prev is None:
                continue

            for line in self.config.counting_lines:
                name = line["name"]
                p1 = line["p1"]
                p2 = line["p2"]

                direction = _crosses_line(prev, curr, p1, p2)
                if direction == 1:
                    self._line_counts[name]["in"] += 1
                elif direction == -1:
                    self._line_counts[name]["out"] += 1

        stale = [tid for tid in self._prev_centroids if tid not in tracks]
        for tid in stale:
            del self._prev_centroids[tid]

        if now - self._last_minute_ts >= 60:
            for name, counts in self._line_counts.items():
                self._time_series[name].append({
                    "timestamp": now,
                    "in": counts["in"],
                    "out": counts["out"],
                    "net": counts["in"] - counts["out"],
                })
                if len(self._time_series[name]) > 60:
                    self._time_series[name] = self._time_series[name][-60:]
            self._last_minute_ts = now

        lines_data = {}
        for name, counts in self._line_counts.items():
            lines_data[name] = {
                "in": counts["in"],
                "out": counts["out"],
                "net": counts["in"] - counts["out"],
            }

        self._display_data = {"lines": lines_data}
        return {"lines": lines_data, "time_series": self._time_series}
