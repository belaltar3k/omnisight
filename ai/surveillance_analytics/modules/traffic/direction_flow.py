from __future__ import annotations

import math

import numpy as np

from surveillance_analytics.core.tracker import VEHICLE_CLASS_IDS, PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase

COMPASS_BINS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _angle_to_compass(angle_deg: float) -> str:
    idx = int((angle_deg + 22.5) % 360 / 45)
    return COMPASS_BINS[idx]


class DirectionalFlow(ModuleBase):
    NAME = "directional_flow"
    TIER = "medium"

    def __init__(self, config):
        super().__init__(config)
        self._vehicle_directions: dict[str, int] = {d: 0 for d in COMPASS_BINS}
        self._person_directions: dict[str, int] = {d: 0 for d in COMPASS_BINS}
        self._total_vehicle_samples = 0
        self._total_person_samples = 0
        self._wrong_way_count = 0
        self._angle_threshold = 150.0

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        vehicle_angles: list[float] = []
        person_angles: list[float] = []

        for tid, track in tracks.items():
            if len(track.centroid_history) < 8:
                continue
            h = track.centroid_history
            dx = h[-1][0] - h[-8][0]
            dy = h[-1][1] - h[-8][1]
            if abs(dx) < 3 and abs(dy) < 3:
                continue

            angle = math.degrees(math.atan2(-dy, dx)) % 360
            compass = _angle_to_compass(angle)

            if track.class_id in VEHICLE_CLASS_IDS:
                self._vehicle_directions[compass] += 1
                self._total_vehicle_samples += 1
                vehicle_angles.append(angle)
            elif track.class_id == PERSON_CLASS_ID:
                self._person_directions[compass] += 1
                self._total_person_samples += 1
                person_angles.append(angle)

        # Dominant direction and wrong-way analysis
        dominant_vehicle = max(self._vehicle_directions, key=self._vehicle_directions.get) if self._total_vehicle_samples > 0 else "N/A"
        dominant_person = max(self._person_directions, key=self._person_directions.get) if self._total_person_samples > 0 else "N/A"

        # Direction entropy (0 = all same direction, higher = more random)
        vehicle_entropy = self._calc_entropy(self._vehicle_directions)
        person_entropy = self._calc_entropy(self._person_directions)

        # Wrong-way detection (vehicles going against dominant flow)
        if vehicle_angles and len(vehicle_angles) >= 2:
            median_angle = float(np.median(vehicle_angles))
            for angle in vehicle_angles:
                diff = abs(angle - median_angle)
                if diff > 180:
                    diff = 360 - diff
                if diff > self._angle_threshold:
                    self._wrong_way_count += 1

        wrong_way_rate = self._wrong_way_count / max(self._total_vehicle_samples, 1)

        stats = {
            "vehicle_direction_distribution": {
                k: round(v / max(self._total_vehicle_samples, 1) * 100, 1)
                for k, v in self._vehicle_directions.items()
            },
            "person_direction_distribution": {
                k: round(v / max(self._total_person_samples, 1) * 100, 1)
                for k, v in self._person_directions.items()
            },
            "vehicle_direction_counts": dict(self._vehicle_directions),
            "person_direction_counts": dict(self._person_directions),
            "dominant_vehicle_direction": dominant_vehicle,
            "dominant_person_direction": dominant_person,
            "vehicle_entropy": round(vehicle_entropy, 3),
            "person_entropy": round(person_entropy, 3),
            "wrong_way_count": self._wrong_way_count,
            "wrong_way_rate": round(wrong_way_rate, 4),
            "total_vehicle_samples": self._total_vehicle_samples,
            "total_person_samples": self._total_person_samples,
        }

        if wrong_way_rate > 0.05:
            self._alerts.append({
                "type": "wrong_way_anomaly",
                "message": f"Elevated wrong-way traffic: {wrong_way_rate:.1%} of vehicles",
                "severity": "warning",
                "confidence": min(wrong_way_rate * 5, 1.0),
                "metadata": {"wrong_way_rate": round(wrong_way_rate, 4)},
            })

        self._display_data = stats
        return stats

    def _calc_entropy(self, counts: dict[str, int]) -> float:
        total = sum(counts.values())
        if total == 0:
            return 0.0
        probs = [v / total for v in counts.values() if v > 0]
        return float(-sum(p * math.log2(p) for p in probs))
