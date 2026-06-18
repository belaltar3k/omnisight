from __future__ import annotations

import math

import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class QueueMonitor(ModuleBase):
    NAME = "queue_monitor"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._cluster_dist = 80
        self._min_cluster_size = 3
        self._r_squared_threshold = 0.7

    def _cluster_persons(self, centroids: list[tuple[int, int]]) -> list[list[int]]:
        if not centroids:
            return []

        n = len(centroids)
        visited = [False] * n
        clusters: list[list[int]] = []

        for i in range(n):
            if visited[i]:
                continue
            cluster = [i]
            visited[i] = True
            queue = [i]
            while queue:
                ci = queue.pop(0)
                for j in range(n):
                    if visited[j]:
                        continue
                    dist = math.hypot(
                        centroids[ci][0] - centroids[j][0],
                        centroids[ci][1] - centroids[j][1],
                    )
                    if dist < self._cluster_dist:
                        visited[j] = True
                        cluster.append(j)
                        queue.append(j)
            clusters.append(cluster)

        return clusters

    def _check_linearity(self, points: list[tuple[int, int]]) -> float:
        if len(points) < 3:
            return 0.0
        xs = np.array([p[0] for p in points], dtype=float)
        ys = np.array([p[1] for p in points], dtype=float)

        # Try both orientations
        if np.std(xs) > np.std(ys):
            coeffs = np.polyfit(xs, ys, 1)
            y_pred = np.polyval(coeffs, xs)
            ss_res = np.sum((ys - y_pred) ** 2)
            ss_tot = np.sum((ys - np.mean(ys)) ** 2)
        else:
            coeffs = np.polyfit(ys, xs, 1)
            x_pred = np.polyval(coeffs, ys)
            ss_res = np.sum((xs - x_pred) ** 2)
            ss_tot = np.sum((xs - np.mean(xs)) ** 2)

        if ss_tot < 1e-6:
            return 1.0
        return max(0.0, 1.0 - ss_res / ss_tot)

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        centroids = []
        person_ids = []
        for tid, track in tracks.items():
            if track.class_id == PERSON_CLASS_ID:
                centroids.append(track.centroid)
                person_ids.append(tid)

        if len(centroids) < self._min_cluster_size:
            self._display_data = {"queue_length": 0}
            return {"queue_length": 0, "queues": []}

        clusters = self._cluster_persons(centroids)
        queues = []
        max_queue_len = 0

        for cluster_indices in clusters:
            if len(cluster_indices) < self._min_cluster_size:
                continue

            cluster_points = [centroids[i] for i in cluster_indices]
            r_sq = self._check_linearity(cluster_points)

            if r_sq >= self._r_squared_threshold:
                queue_len = len(cluster_indices)
                centroid_x = int(np.mean([p[0] for p in cluster_points]))
                centroid_y = int(np.mean([p[1] for p in cluster_points]))
                queues.append({
                    "length": queue_len,
                    "r_squared": round(r_sq, 3),
                    "centroid": (centroid_x, centroid_y),
                })
                max_queue_len = max(max_queue_len, queue_len)

        if max_queue_len > self.config.queue_max_length:
            self._alerts.append({
                "type": "queue_long",
                "message": f"Queue length {max_queue_len} exceeds max {self.config.queue_max_length}",
                "severity": "warning",
                "confidence": min(max_queue_len / (self.config.queue_max_length * 2), 1.0),
                "metadata": {"queue_length": max_queue_len},
            })

        self._display_data = {"queue_length": max_queue_len, "queues": queues}
        return {"queue_length": max_queue_len, "queues": queues}
