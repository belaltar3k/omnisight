from __future__ import annotations

import math
import time
from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class CrossingUsage(ModuleBase):
    NAME = "crossing_usage"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._crosswalk_poly = np.array(config.zones.get("crosswalk", []), dtype=np.int32)
        self._persons_in_crosswalk: dict[int, float] = {}  # tid -> enter_time
        self._total_crossings = 0
        self._crossing_durations: deque = deque(maxlen=500)
        self._hourly_crossings: deque = deque(maxlen=24)
        self._current_hour_count = 0
        self._last_hour_ts = time.time()
        self._proximity_events = 0
        self._proximity_dist = 120

    def _in_crosswalk(self, cx: int, cy: int) -> bool:
        if len(self._crosswalk_poly) < 3:
            return False
        return cv2.pointPolygonTest(self._crosswalk_poly, (float(cx), float(cy)), False) >= 0

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()
        currently_crossing = 0

        for tid, track in tracks.items():
            if track.class_id != PERSON_CLASS_ID:
                continue

            in_cw = self._in_crosswalk(track.centroid[0], track.centroid[1])

            if in_cw:
                if tid not in self._persons_in_crosswalk:
                    self._persons_in_crosswalk[tid] = now
                currently_crossing += 1
            else:
                if tid in self._persons_in_crosswalk:
                    duration = now - self._persons_in_crosswalk[tid]
                    if duration > 0.5:
                        self._total_crossings += 1
                        self._current_hour_count += 1
                        self._crossing_durations.append(duration)
                    del self._persons_in_crosswalk[tid]

        # Clean stale
        stale = [tid for tid in self._persons_in_crosswalk if tid not in tracks]
        for tid in stale:
            duration = now - self._persons_in_crosswalk[tid]
            if duration > 0.5:
                self._total_crossings += 1
                self._current_hour_count += 1
                self._crossing_durations.append(duration)
            del self._persons_in_crosswalk[tid]

        # Pedestrian-vehicle proximity in crosswalk
        crosswalk_persons = [t for t in tracks.values() if t.class_id == PERSON_CLASS_ID
                             and self._in_crosswalk(t.centroid[0], t.centroid[1])]
        for person in crosswalk_persons:
            for tid, veh in tracks.items():
                if veh.class_id not in VEHICLE_CLASS_IDS:
                    continue
                dist = math.hypot(person.centroid[0] - veh.centroid[0],
                                  person.centroid[1] - veh.centroid[1])
                if dist < self._proximity_dist and veh.speed_kmh > 10:
                    self._proximity_events += 1

        # Hourly rollover
        if now - self._last_hour_ts >= 3600:
            self._hourly_crossings.append({
                "timestamp": now,
                "count": self._current_hour_count,
            })
            self._current_hour_count = 0
            self._last_hour_ts = now

        avg_crossing_time = float(np.mean(list(self._crossing_durations))) if self._crossing_durations else 0
        elapsed_hours = max((now - (self._hourly_crossings[0]["timestamp"] if self._hourly_crossings else now)) / 3600, 0.01)
        crossings_per_hour = self._total_crossings / elapsed_hours if elapsed_hours > 0.1 else 0

        stats = {
            "currently_crossing": currently_crossing,
            "total_crossings": self._total_crossings,
            "crossings_per_hour": round(crossings_per_hour, 1),
            "avg_crossing_time_sec": round(avg_crossing_time, 1),
            "median_crossing_time_sec": round(float(np.median(list(self._crossing_durations))), 1) if self._crossing_durations else 0,
            "pedestrian_vehicle_proximity_events": self._proximity_events,
            "hourly_series": list(self._hourly_crossings)[-12:],
        }

        self._display_data = stats
        return stats
