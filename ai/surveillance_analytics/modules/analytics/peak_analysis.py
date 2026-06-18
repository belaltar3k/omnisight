from __future__ import annotations

import time
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class PeakAnalysis(ModuleBase):
    NAME = "peak_analysis"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._minute_person_counts: deque = deque(maxlen=1440)  # 24 hours
        self._minute_vehicle_counts: deque = deque(maxlen=1440)
        self._current_minute_persons: list[int] = []
        self._current_minute_vehicles: list[int] = []
        self._last_minute_ts = time.time()
        self._5min_person_counts: deque = deque(maxlen=288)
        self._5min_vehicle_counts: deque = deque(maxlen=288)
        self._last_5min_ts = time.time()
        self._5min_persons: list[int] = []
        self._5min_vehicles: list[int] = []

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()

        persons = sum(1 for t in tracks.values() if t.class_id == PERSON_CLASS_ID)
        vehicles = sum(1 for t in tracks.values() if t.class_id in VEHICLE_CLASS_IDS)

        self._current_minute_persons.append(persons)
        self._current_minute_vehicles.append(vehicles)
        self._5min_persons.append(persons)
        self._5min_vehicles.append(vehicles)

        # Minute rollover
        if now - self._last_minute_ts >= 60:
            if self._current_minute_persons:
                self._minute_person_counts.append({
                    "timestamp": now,
                    "avg": round(float(np.mean(self._current_minute_persons)), 1),
                    "max": max(self._current_minute_persons),
                })
                self._minute_vehicle_counts.append({
                    "timestamp": now,
                    "avg": round(float(np.mean(self._current_minute_vehicles)), 1),
                    "max": max(self._current_minute_vehicles),
                })
            self._current_minute_persons = []
            self._current_minute_vehicles = []
            self._last_minute_ts = now

        # 5-minute rollover
        if now - self._last_5min_ts >= 300:
            if self._5min_persons:
                self._5min_person_counts.append({
                    "timestamp": now,
                    "avg": round(float(np.mean(self._5min_persons)), 1),
                    "max": max(self._5min_persons),
                })
                self._5min_vehicle_counts.append({
                    "timestamp": now,
                    "avg": round(float(np.mean(self._5min_vehicles)), 1),
                    "max": max(self._5min_vehicles),
                })
            self._5min_persons = []
            self._5min_vehicles = []
            self._last_5min_ts = now

        # Find peak periods
        person_mins = list(self._minute_person_counts)
        vehicle_mins = list(self._minute_vehicle_counts)

        peak_person_minute = max(person_mins, key=lambda x: x["avg"]) if person_mins else {"avg": 0, "timestamp": 0}
        peak_vehicle_minute = max(vehicle_mins, key=lambda x: x["avg"]) if vehicle_mins else {"avg": 0, "timestamp": 0}

        # Activity distribution across 5-min blocks
        person_5min_avgs = [p["avg"] for p in self._5min_person_counts] if self._5min_person_counts else [0]
        vehicle_5min_avgs = [v["avg"] for v in self._5min_vehicle_counts] if self._5min_vehicle_counts else [0]

        # Current period classification
        recent_person_avg = float(np.mean(self._current_minute_persons)) if self._current_minute_persons else 0
        overall_person_avg = float(np.mean(person_5min_avgs)) if person_5min_avgs else 0
        if overall_person_avg > 0:
            activity_ratio = recent_person_avg / overall_person_avg
        else:
            activity_ratio = 1.0

        if activity_ratio > 1.5:
            period_class = "peak"
        elif activity_ratio < 0.5:
            period_class = "low"
        else:
            period_class = "normal"

        stats = {
            "current_persons": persons,
            "current_vehicles": vehicles,
            "current_period": period_class,
            "activity_ratio": round(activity_ratio, 2),
            "peak_person_minute": {
                "avg": peak_person_minute["avg"],
                "minutes_ago": round((now - peak_person_minute.get("timestamp", now)) / 60, 0),
            },
            "peak_vehicle_minute": {
                "avg": peak_vehicle_minute["avg"],
                "minutes_ago": round((now - peak_vehicle_minute.get("timestamp", now)) / 60, 0),
            },
            "person_5min_trend": [{"avg": p["avg"]} for p in list(self._5min_person_counts)[-12:]],
            "vehicle_5min_trend": [{"avg": v["avg"]} for v in list(self._5min_vehicle_counts)[-12:]],
            "observation_minutes": len(person_mins),
        }

        self._display_data = stats
        return stats
