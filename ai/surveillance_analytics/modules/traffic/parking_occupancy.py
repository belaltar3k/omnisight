from __future__ import annotations

import time
from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class ParkingOccupancy(ModuleBase):
    NAME = "parking_occupancy"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._no_parking_poly = np.array(config.zones.get("no_parking", []), dtype=np.int32)
        self._parked_vehicles: dict[int, float] = {}  # tid -> enter_time
        self._stop_threshold_px = 3.0
        self._total_park_events = 0
        self._total_park_duration = 0.0
        self._occupancy_series: deque = deque(maxlen=120)
        self._last_sample_ts = time.time()
        self._max_simultaneous = 0
        self._capacity = 5

    def _in_zone(self, cx: int, cy: int) -> bool:
        if len(self._no_parking_poly) < 3:
            return False
        return cv2.pointPolygonTest(self._no_parking_poly, (float(cx), float(cy)), False) >= 0

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        import math
        now = time.time()
        current_parked = 0

        for tid, track in tracks.items():
            if track.class_id not in VEHICLE_CLASS_IDS:
                continue
            if not self._in_zone(track.centroid[0], track.centroid[1]):
                if tid in self._parked_vehicles:
                    duration = now - self._parked_vehicles[tid]
                    self._total_park_duration += duration
                    self._total_park_events += 1
                    del self._parked_vehicles[tid]
                continue

            speed_px = math.hypot(*track.velocity_px)
            if speed_px < self._stop_threshold_px:
                if tid not in self._parked_vehicles:
                    self._parked_vehicles[tid] = now
                current_parked += 1
            else:
                if tid in self._parked_vehicles:
                    duration = now - self._parked_vehicles[tid]
                    self._total_park_duration += duration
                    self._total_park_events += 1
                    del self._parked_vehicles[tid]

        # Clean stale
        stale = [tid for tid in self._parked_vehicles if tid not in tracks]
        for tid in stale:
            duration = now - self._parked_vehicles[tid]
            self._total_park_duration += duration
            self._total_park_events += 1
            del self._parked_vehicles[tid]

        self._max_simultaneous = max(self._max_simultaneous, current_parked)
        utilization = current_parked / max(self._capacity, 1)

        if now - self._last_sample_ts >= 60:
            self._occupancy_series.append({
                "timestamp": now,
                "count": current_parked,
                "utilization": round(utilization, 2),
            })
            self._last_sample_ts = now

        avg_duration = self._total_park_duration / max(self._total_park_events, 1)
        turnover = self._total_park_events / max((now - (self._occupancy_series[0]["timestamp"] if self._occupancy_series else now)) / 3600, 0.01)

        stats = {
            "current_parked": current_parked,
            "utilization_pct": round(utilization * 100, 1),
            "max_simultaneous": self._max_simultaneous,
            "total_park_events": self._total_park_events,
            "avg_duration_sec": round(avg_duration, 1),
            "avg_duration_min": round(avg_duration / 60, 1),
            "turnover_per_hour": round(turnover, 2),
            "occupancy_series": list(self._occupancy_series)[-10:],
        }

        if utilization > 0.9:
            self._alerts.append({
                "type": "parking_full",
                "message": f"Parking zone near capacity: {utilization:.0%} utilized",
                "severity": "info",
                "confidence": utilization,
                "metadata": {"utilization": round(utilization, 2), "count": current_parked},
            })

        self._display_data = stats
        return stats
