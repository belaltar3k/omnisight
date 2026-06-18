from __future__ import annotations

import math
import time
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import PERSON_CLASS_ID, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class QueueAnalytics(ModuleBase):
    NAME = "queue_analytics"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._cluster_dist = 80
        self._min_cluster_size = 3
        self._r_squared_threshold = 0.7
        self._length_history: deque = deque(maxlen=500)
        self._minute_series: deque = deque(maxlen=60)
        self._last_minute_ts = time.time()
        self._current_minute_lengths: list[int] = []
        self._peak_length = 0
        self._total_queue_observations = 0

    def _cluster_persons(self, centroids: list[tuple[int, int]]) -> list[list[int]]:
        n = len(centroids)
        if n < 2:
            return []
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
                    dist = math.hypot(centroids[ci][0] - centroids[j][0],
                                      centroids[ci][1] - centroids[j][1])
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
        now = time.time()

        centroids = [track.centroid for track in tracks.values() if track.class_id == PERSON_CLASS_ID]
        if len(centroids) < self._min_cluster_size:
            self._display_data = {"queue_length": 0, "queues": []}
            return {"queue_length": 0, "queues": [], "avg_length": 0}

        clusters = self._cluster_persons(centroids)
        queues = []
        max_queue_len = 0

        for indices in clusters:
            if len(indices) < self._min_cluster_size:
                continue
            pts = [centroids[i] for i in indices]
            r_sq = self._check_linearity(pts)
            if r_sq >= self._r_squared_threshold:
                queue_len = len(indices)
                cx = int(np.mean([p[0] for p in pts]))
                cy = int(np.mean([p[1] for p in pts]))
                queues.append({
                    "length": queue_len,
                    "r_squared": round(r_sq, 3),
                    "centroid": (cx, cy),
                })
                max_queue_len = max(max_queue_len, queue_len)

        self._length_history.append(max_queue_len)
        self._current_minute_lengths.append(max_queue_len)
        self._peak_length = max(self._peak_length, max_queue_len)
        if max_queue_len > 0:
            self._total_queue_observations += 1

        # Minute aggregation
        if now - self._last_minute_ts >= 60:
            if self._current_minute_lengths:
                arr = np.array(self._current_minute_lengths)
                self._minute_series.append({
                    "timestamp": now,
                    "avg_length": round(float(np.mean(arr)), 1),
                    "max_length": int(np.max(arr)),
                })
            self._current_minute_lengths = []
            self._last_minute_ts = now

        avg_length = float(np.mean(list(self._length_history))) if self._length_history else 0
        # Rough wait time estimate: ~30 seconds per person in queue
        est_wait_sec = max_queue_len * 30

        stats = {
            "current_queue_length": max_queue_len,
            "queue_count": len(queues),
            "queues": queues,
            "avg_queue_length": round(avg_length, 1),
            "peak_queue_length": self._peak_length,
            "estimated_wait_sec": est_wait_sec,
            "estimated_wait_min": round(est_wait_sec / 60, 1),
            "queue_presence_rate": round(self._total_queue_observations / max(len(self._length_history), 1), 2),
            "minute_series": list(self._minute_series)[-10:],
        }

        if max_queue_len > self.config.queue_max_length:
            self._alerts.append({
                "type": "long_queue",
                "message": f"Queue length {max_queue_len} exceeds threshold {self.config.queue_max_length} (est wait: {est_wait_sec // 60}min)",
                "severity": "info",
                "confidence": min(max_queue_len / (self.config.queue_max_length * 2), 1.0),
                "metadata": {"length": max_queue_len, "wait_min": round(est_wait_sec / 60, 1)},
            })

        self._display_data = stats
        return stats
