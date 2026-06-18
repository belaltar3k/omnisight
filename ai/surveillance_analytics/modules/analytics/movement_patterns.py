from __future__ import annotations

import math
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, VEHICLE_CLASS_IDS, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class MovementPatterns(ModuleBase):
    NAME = "movement_patterns"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._completed_trajectories: deque = deque(maxlen=500)
        self._active_track_start: dict[int, tuple[int, int]] = {}
        self._speed_by_region: dict[tuple[int, int], deque] = {}
        self._grid_size = 80
        self._total_distance: dict[str, float] = {"person": 0, "vehicle": 0}
        self._total_tracks: dict[str, int] = {"person": 0, "vehicle": 0}

    def _grid_key(self, cx: int, cy: int) -> tuple[int, int]:
        return (cx // self._grid_size, cy // self._grid_size)

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        current_ids = set()

        for tid, track in tracks.items():
            current_ids.add(tid)

            if tid not in self._active_track_start:
                self._active_track_start[tid] = track.centroid

            # Record speed by grid region
            gk = self._grid_key(track.centroid[0], track.centroid[1])
            if gk not in self._speed_by_region:
                self._speed_by_region[gk] = deque(maxlen=100)
            self._speed_by_region[gk].append(track.speed_kmh)

        # Complete trajectories for departed tracks
        departed = [tid for tid in self._active_track_start if tid not in current_ids]
        for tid in departed:
            start = self._active_track_start.pop(tid)
            if tid in tracks:
                end = tracks[tid].centroid
            else:
                end = start

            displacement = math.hypot(end[0] - start[0], end[1] - start[1])
            if displacement > 30:
                category = "person"
                if tid in tracks and tracks[tid].class_id in VEHICLE_CLASS_IDS:
                    category = "vehicle"
                self._completed_trajectories.append({
                    "start": start,
                    "end": end,
                    "displacement_px": round(displacement, 1),
                    "category": category,
                })
                self._total_distance[category] += displacement
                self._total_tracks[category] += 1

        # Compute corridor analysis: find grid regions with highest average speed
        speed_grid: dict[tuple[int, int], float] = {}
        for gk, speeds in self._speed_by_region.items():
            if speeds:
                speed_grid[gk] = float(np.mean(list(speeds)))

        # Top corridors (fastest moving regions)
        fast_regions = sorted(speed_grid.items(), key=lambda x: x[1], reverse=True)[:5]
        slow_regions = sorted(speed_grid.items(), key=lambda x: x[1])[:5]

        # Average displacement per category
        traj_list = list(self._completed_trajectories)
        person_displacements = [t["displacement_px"] for t in traj_list if t["category"] == "person"]
        vehicle_displacements = [t["displacement_px"] for t in traj_list if t["category"] == "vehicle"]

        # Start-end vector analysis: common origin-destination pairs
        od_pairs: dict[str, int] = {}
        for t in traj_list[-100:]:
            sk = self._grid_key(t["start"][0], t["start"][1])
            ek = self._grid_key(t["end"][0], t["end"][1])
            key = f"{sk}->{ek}"
            od_pairs[key] = od_pairs.get(key, 0) + 1

        top_od = sorted(od_pairs.items(), key=lambda x: x[1], reverse=True)[:5]

        stats = {
            "total_completed_trajectories": len(traj_list),
            "person_tracks": self._total_tracks["person"],
            "vehicle_tracks": self._total_tracks["vehicle"],
            "avg_person_displacement_px": round(float(np.mean(person_displacements)), 1) if person_displacements else 0,
            "avg_vehicle_displacement_px": round(float(np.mean(vehicle_displacements)), 1) if vehicle_displacements else 0,
            "fast_regions": [{"grid": list(r[0]), "avg_speed": round(r[1], 1)} for r in fast_regions],
            "slow_regions": [{"grid": list(r[0]), "avg_speed": round(r[1], 1)} for r in slow_regions],
            "top_origin_destination_pairs": [{"pair": p[0], "count": p[1]} for p in top_od],
            "active_tracks": len(self._active_track_start),
            "grid_coverage": len(speed_grid),
        }

        self._display_data = stats
        return stats
