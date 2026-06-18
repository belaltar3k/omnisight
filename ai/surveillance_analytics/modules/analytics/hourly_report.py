from __future__ import annotations

import time
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class HourlyReport(ModuleBase):
    NAME = "hourly_report"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._hour_start = time.time()
        self._hourly_reports: deque = deque(maxlen=24)

        self._person_samples: list[int] = []
        self._vehicle_samples: list[int] = []
        self._speed_samples: list[float] = []
        self._unique_persons: set[int] = set()
        self._unique_vehicles: set[int] = set()

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()

        persons = sum(1 for t in tracks.values() if t.class_id == PERSON_CLASS_ID)
        vehicles = sum(1 for t in tracks.values() if t.class_id in VEHICLE_CLASS_IDS)

        self._person_samples.append(persons)
        self._vehicle_samples.append(vehicles)

        for tid, track in tracks.items():
            if track.class_id == PERSON_CLASS_ID:
                self._unique_persons.add(tid)
            elif track.class_id in VEHICLE_CLASS_IDS:
                self._unique_vehicles.add(tid)
                if track.speed_kmh > 2:
                    self._speed_samples.append(track.speed_kmh)

        # Hourly rollover
        if now - self._hour_start >= 3600:
            report = self._compile_report(now)
            self._hourly_reports.append(report)
            self._reset_hour(now)

        # Compile current partial report
        current = self._compile_report(now)

        stats = {
            "current_hour": current,
            "completed_hours": list(self._hourly_reports),
            "total_hours_observed": len(self._hourly_reports),
        }

        self._display_data = stats
        return stats

    def _compile_report(self, now: float) -> dict:
        elapsed_min = (now - self._hour_start) / 60

        p_arr = np.array(self._person_samples) if self._person_samples else np.array([0])
        v_arr = np.array(self._vehicle_samples) if self._vehicle_samples else np.array([0])
        s_arr = np.array(self._speed_samples) if self._speed_samples else np.array([0])

        return {
            "elapsed_minutes": round(elapsed_min, 1),
            "persons": {
                "avg": round(float(np.mean(p_arr)), 1),
                "max": int(np.max(p_arr)),
                "min": int(np.min(p_arr)),
                "std": round(float(np.std(p_arr)), 1),
                "unique": len(self._unique_persons),
            },
            "vehicles": {
                "avg": round(float(np.mean(v_arr)), 1),
                "max": int(np.max(v_arr)),
                "min": int(np.min(v_arr)),
                "std": round(float(np.std(v_arr)), 1),
                "unique": len(self._unique_vehicles),
            },
            "speed": {
                "avg": round(float(np.mean(s_arr)), 1),
                "median": round(float(np.median(s_arr)), 1),
                "max": round(float(np.max(s_arr)), 1),
                "p90": round(float(np.percentile(s_arr, 90)), 1) if len(s_arr) > 1 else 0,
            },
            "total_samples": len(self._person_samples),
        }

    def _reset_hour(self, now: float):
        self._hour_start = now
        self._person_samples = []
        self._vehicle_samples = []
        self._speed_samples = []
        self._unique_persons = set()
        self._unique_vehicles = set()
