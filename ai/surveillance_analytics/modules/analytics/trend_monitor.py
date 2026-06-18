from __future__ import annotations

import time
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class TrendMonitor(ModuleBase):
    NAME = "trend_monitor"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._person_counts: deque = deque(maxlen=1800)
        self._vehicle_counts: deque = deque(maxlen=1800)
        self._speed_avgs: deque = deque(maxlen=1800)
        self._timestamps: deque = deque(maxlen=1800)

    def _compute_trend(self, series: list[float], window: int = 300) -> dict:
        if len(series) < 20:
            return {"direction": "insufficient_data", "rate": 0, "rolling_avg": 0}

        recent = series[-min(window, len(series)):]
        rolling_avg = float(np.mean(recent))

        half = len(recent) // 2
        if half < 5:
            return {"direction": "stable", "rate": 0, "rolling_avg": round(rolling_avg, 2)}

        first_half_avg = float(np.mean(recent[:half]))
        second_half_avg = float(np.mean(recent[half:]))

        if first_half_avg > 0:
            rate = (second_half_avg - first_half_avg) / first_half_avg
        else:
            rate = 0

        if rate > 0.1:
            direction = "increasing"
        elif rate < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "rate_pct": round(rate * 100, 1),
            "rolling_avg": round(rolling_avg, 2),
            "first_half_avg": round(first_half_avg, 2),
            "second_half_avg": round(second_half_avg, 2),
        }

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        persons = sum(1 for t in tracks.values() if t.class_id == PERSON_CLASS_ID)
        vehicles = sum(1 for t in tracks.values() if t.class_id in VEHICLE_CLASS_IDS)

        vehicle_speeds = [t.speed_kmh for t in tracks.values() if t.class_id in VEHICLE_CLASS_IDS and t.speed_kmh > 2]
        avg_speed = float(np.mean(vehicle_speeds)) if vehicle_speeds else 0

        self._person_counts.append(persons)
        self._vehicle_counts.append(vehicles)
        self._speed_avgs.append(avg_speed)

        person_trend = self._compute_trend(list(self._person_counts))
        vehicle_trend = self._compute_trend(list(self._vehicle_counts))
        speed_trend = self._compute_trend(list(self._speed_avgs))

        # Short-term trend (last 30s vs previous 30s)
        person_short = self._compute_trend(list(self._person_counts), window=60)
        vehicle_short = self._compute_trend(list(self._vehicle_counts), window=60)

        stats = {
            "person_trend": person_trend,
            "vehicle_trend": vehicle_trend,
            "speed_trend": speed_trend,
            "person_short_term": person_short,
            "vehicle_short_term": vehicle_short,
            "samples_collected": len(self._person_counts),
        }

        # Alert on significant changes
        for name, trend in [("person", person_short), ("vehicle", vehicle_short)]:
            rate = trend.get("rate_pct", 0)
            if abs(rate) > 50:
                self._alerts.append({
                    "type": f"{name}_trend_spike",
                    "message": f"{name.title()} count {trend['direction']} rapidly ({rate:+.0f}%)",
                    "severity": "info",
                    "confidence": min(abs(rate) / 100, 1.0),
                    "metadata": {"trend": trend, "type": name},
                })

        self._display_data = stats
        return stats
