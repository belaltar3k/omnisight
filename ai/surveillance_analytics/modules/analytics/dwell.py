from __future__ import annotations

import time

import cv2
import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class DwellTime(ModuleBase):
    NAME = "dwell_time"
    TIER = "fast"

    def __init__(self, config):
        super().__init__(config)
        self._entry_times: dict[int, dict[str, float]] = {}
        self._dwell_records: dict[str, list[float]] = {}
        self._zone_polys: dict[str, np.ndarray] = {}

        for zone_name, pts in config.zones.items():
            if len(pts) >= 3:
                self._zone_polys[zone_name] = np.array(pts, dtype=np.int32)

    def _get_zone(self, cx: int, cy: int) -> str | None:
        for zone_name, poly in self._zone_polys.items():
            if cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0:
                return zone_name
        return None

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()
        dwell_data: dict[int, dict[str, float]] = {}

        active_person_ids = set()
        for tid, track in tracks.items():
            if track.class_id != PERSON_CLASS_ID:
                continue
            active_person_ids.add(tid)

            zone = self._get_zone(track.centroid[0], track.centroid[1])
            if tid not in self._entry_times:
                self._entry_times[tid] = {}

            if zone:
                if zone not in self._entry_times[tid]:
                    self._entry_times[tid][zone] = now

                dwell = now - self._entry_times[tid][zone]
                if tid not in dwell_data:
                    dwell_data[tid] = {}
                dwell_data[tid][zone] = dwell

                if dwell > self.config.dwell_alert_sec:
                    self._alerts.append({
                        "type": "loitering",
                        "message": f"Person {tid} dwelling in {zone} for {dwell:.0f}s",
                        "severity": "warning",
                        "confidence": min(dwell / (self.config.dwell_alert_sec * 2), 0.9),
                        "zone": zone,
                        "metadata": {"track_id": tid, "zone": zone, "dwell_sec": round(dwell, 1)},
                    })

            # Record exits
            for z in list(self._entry_times.get(tid, {}).keys()):
                if z != zone:
                    entry = self._entry_times[tid].pop(z, None)
                    if entry:
                        dwell_val = now - entry
                        if z not in self._dwell_records:
                            self._dwell_records[z] = []
                        self._dwell_records[z].append(dwell_val)
                        if len(self._dwell_records[z]) > 100:
                            self._dwell_records[z] = self._dwell_records[z][-100:]

        stale = [tid for tid in self._entry_times if tid not in active_person_ids]
        for tid in stale:
            del self._entry_times[tid]

        zone_averages = {}
        for z, records in self._dwell_records.items():
            if records:
                zone_averages[z] = round(sum(records) / len(records), 1)

        self._display_data = {"dwell_data": dwell_data, "zone_averages": zone_averages}
        return {"dwell_data": dwell_data, "zone_averages": zone_averages}
