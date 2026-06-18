from __future__ import annotations

import time
from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class ZoneOccupancy(ModuleBase):
    NAME = "zone_occupancy"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._zone_polys: dict[str, np.ndarray] = {}
        self._zone_person_series: dict[str, deque] = {}
        self._zone_vehicle_series: dict[str, deque] = {}
        self._transitions: dict[str, dict[str, int]] = {}
        self._prev_person_zones: dict[int, str] = {}
        self._minute_series: dict[str, deque] = {}
        self._last_minute_ts = time.time()
        self._current_minute_data: dict[str, list[int]] = {}

        for zone_name, pts in config.zones.items():
            if len(pts) >= 3:
                self._zone_polys[zone_name] = np.array(pts, dtype=np.int32)
                self._zone_person_series[zone_name] = deque(maxlen=300)
                self._zone_vehicle_series[zone_name] = deque(maxlen=300)
                self._transitions[zone_name] = {}
                self._minute_series[zone_name] = deque(maxlen=60)
                self._current_minute_data[zone_name] = []

    def _get_zone(self, cx: int, cy: int) -> str | None:
        for zone_name, poly in self._zone_polys.items():
            if cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0:
                return zone_name
        return None

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()
        zone_persons: dict[str, int] = {z: 0 for z in self._zone_polys}
        zone_vehicles: dict[str, int] = {z: 0 for z in self._zone_polys}
        current_person_zones: dict[int, str] = {}

        for tid, track in tracks.items():
            zone = self._get_zone(track.centroid[0], track.centroid[1])
            if zone is None:
                continue

            if track.class_id == PERSON_CLASS_ID:
                zone_persons[zone] += 1
                current_person_zones[tid] = zone
            elif track.class_id in VEHICLE_CLASS_IDS:
                zone_vehicles[zone] += 1

        # Compute zone transitions (person moved from zone A to zone B)
        for tid, new_zone in current_person_zones.items():
            old_zone = self._prev_person_zones.get(tid)
            if old_zone and old_zone != new_zone:
                if new_zone not in self._transitions[old_zone]:
                    self._transitions[old_zone][new_zone] = 0
                self._transitions[old_zone][new_zone] += 1
        self._prev_person_zones = current_person_zones

        # Record series
        for zone_name in self._zone_polys:
            self._zone_person_series[zone_name].append(zone_persons.get(zone_name, 0))
            self._zone_vehicle_series[zone_name].append(zone_vehicles.get(zone_name, 0))
            self._current_minute_data[zone_name].append(zone_persons.get(zone_name, 0))

        # Minute aggregation
        if now - self._last_minute_ts >= 60:
            for zone_name in self._zone_polys:
                data = self._current_minute_data.get(zone_name, [])
                if data:
                    self._minute_series[zone_name].append({
                        "timestamp": now,
                        "avg_persons": round(float(np.mean(data)), 1),
                        "max_persons": max(data),
                    })
                self._current_minute_data[zone_name] = []
            self._last_minute_ts = now

        zone_stats = {}
        for zone_name in self._zone_polys:
            p_series = list(self._zone_person_series[zone_name])
            zone_stats[zone_name] = {
                "current_persons": zone_persons.get(zone_name, 0),
                "current_vehicles": zone_vehicles.get(zone_name, 0),
                "avg_persons": round(float(np.mean(p_series)), 1) if p_series else 0,
                "peak_persons": max(p_series) if p_series else 0,
                "transitions_to": dict(self._transitions.get(zone_name, {})),
            }

        total_persons = sum(zone_persons.values())
        total_vehicles = sum(zone_vehicles.values())

        stats = {
            "total_persons_in_zones": total_persons,
            "total_vehicles_in_zones": total_vehicles,
            "zone_stats": zone_stats,
            "zone_person_distribution": {
                z: round(v / max(total_persons, 1) * 100, 1)
                for z, v in zone_persons.items() if v > 0
            },
        }

        self._display_data = stats
        return stats
