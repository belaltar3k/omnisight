from __future__ import annotations

import math
import time
from collections import deque

import cv2
import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class GatheringStatistics(ModuleBase):
    NAME = "gathering_statistics"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._cluster_dist = 100
        self._min_cluster_size = 3
        self._active_gatherings: dict[str, dict] = {}
        self._total_events = 0
        self._completed_durations: deque = deque(maxlen=200)
        self._completed_sizes: deque = deque(maxlen=200)
        self._zone_event_counts: dict[str, int] = {}

    def _cluster_persons(self, persons: list[tuple[int, tuple[int, int]]]) -> list[list[tuple[int, tuple[int, int]]]]:
        if len(persons) < 2:
            return []
        visited = [False] * len(persons)
        clusters = []
        for i in range(len(persons)):
            if visited[i]:
                continue
            cluster = [persons[i]]
            visited[i] = True
            queue = [i]
            while queue:
                ci = queue.pop(0)
                for j in range(len(persons)):
                    if visited[j]:
                        continue
                    dist = math.hypot(
                        persons[ci][1][0] - persons[j][1][0],
                        persons[ci][1][1] - persons[j][1][1],
                    )
                    if dist < self._cluster_dist:
                        visited[j] = True
                        cluster.append(persons[j])
                        queue.append(j)
            if len(cluster) >= self._min_cluster_size:
                clusters.append(cluster)
        return clusters

    def _get_zone(self, cx: int, cy: int) -> str:
        for zone_name, pts in self.config.zones.items():
            if len(pts) < 3:
                continue
            poly = np.array(pts, dtype=np.int32)
            if cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0:
                return zone_name
        return "unknown"

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()

        persons = [(tid, track.centroid) for tid, track in tracks.items() if track.class_id == PERSON_CLASS_ID]
        clusters = self._cluster_persons(persons)

        current_cluster_keys: set[str] = set()
        active_gatherings: list[dict] = []

        for cluster in clusters:
            centroids = [c[1] for c in cluster]
            cx = int(np.mean([p[0] for p in centroids]))
            cy = int(np.mean([p[1] for p in centroids]))
            key = f"{cx // 50}_{cy // 50}"
            current_cluster_keys.add(key)

            zone = self._get_zone(cx, cy)

            if key not in self._active_gatherings:
                self._active_gatherings[key] = {"start": now, "zone": zone, "peak_size": len(cluster)}

            g = self._active_gatherings[key]
            g["peak_size"] = max(g["peak_size"], len(cluster))
            duration = now - g["start"]

            active_gatherings.append({
                "size": len(cluster),
                "centroid": (cx, cy),
                "duration_sec": round(duration, 1),
                "zone": zone,
            })

        # Complete ended gatherings
        ended = [k for k in self._active_gatherings if k not in current_cluster_keys]
        for k in ended:
            g = self._active_gatherings.pop(k)
            duration = now - g["start"]
            if duration > 5:
                self._total_events += 1
                self._completed_durations.append(duration)
                self._completed_sizes.append(g["peak_size"])
                zone = g.get("zone", "unknown")
                self._zone_event_counts[zone] = self._zone_event_counts.get(zone, 0) + 1

        avg_duration = float(np.mean(list(self._completed_durations))) if self._completed_durations else 0
        avg_size = float(np.mean(list(self._completed_sizes))) if self._completed_sizes else 0

        stats = {
            "active_gatherings": len(active_gatherings),
            "active_details": active_gatherings,
            "total_completed_events": self._total_events,
            "avg_duration_sec": round(avg_duration, 1),
            "avg_group_size": round(avg_size, 1),
            "max_group_size": max(list(self._completed_sizes), default=0),
            "events_by_zone": dict(self._zone_event_counts),
            "largest_current": max([g["size"] for g in active_gatherings], default=0),
        }

        if active_gatherings:
            longest = max(active_gatherings, key=lambda g: g["duration_sec"])
            if longest["duration_sec"] > self.config.loiter_timeout_sec:
                self._alerts.append({
                    "type": "prolonged_gathering",
                    "message": f"Gathering of {longest['size']} persons for {longest['duration_sec']:.0f}s in {longest['zone']}",
                    "severity": "info",
                    "confidence": min(longest["duration_sec"] / 300, 1.0),
                    "metadata": stats,
                })

        self._display_data = stats
        return stats
