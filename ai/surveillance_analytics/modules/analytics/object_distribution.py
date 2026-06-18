from __future__ import annotations

import time
from collections import deque

import numpy as np

from surveillance_analytics.core.tracker import COCO_NAMES, TrackInfo
from surveillance_analytics.modules.base import ModuleBase


class ObjectDistribution(ModuleBase):
    NAME = "object_distribution"
    TIER = "slow"

    def __init__(self, config):
        super().__init__(config)
        self._class_counts: dict[str, int] = {}
        self._class_frame_counts: dict[str, int] = {}
        self._total_frames = 0
        self._unique_by_class: dict[str, set] = {}
        self._minute_series: deque = deque(maxlen=60)
        self._current_minute_data: dict[str, list[int]] = {}
        self._last_minute_ts = time.time()

    def process(self, frame: np.ndarray, detections: list[dict], tracks: dict[int, TrackInfo]) -> dict:
        now = time.time()
        self._total_frames += 1

        frame_class_counts: dict[str, int] = {}

        for d in detections:
            cls_name = COCO_NAMES.get(d["class_id"], f"class_{d['class_id']}")
            frame_class_counts[cls_name] = frame_class_counts.get(cls_name, 0) + 1
            self._class_counts[cls_name] = self._class_counts.get(cls_name, 0) + 1

            tid = d.get("track_id", -1)
            if tid >= 0:
                if cls_name not in self._unique_by_class:
                    self._unique_by_class[cls_name] = set()
                self._unique_by_class[cls_name].add(tid)

        for cls_name in frame_class_counts:
            self._class_frame_counts[cls_name] = self._class_frame_counts.get(cls_name, 0) + 1
            if cls_name not in self._current_minute_data:
                self._current_minute_data[cls_name] = []
            self._current_minute_data[cls_name].append(frame_class_counts[cls_name])

        # Minute rollover
        if now - self._last_minute_ts >= 60:
            minute_snapshot = {}
            for cls_name, counts in self._current_minute_data.items():
                if counts:
                    minute_snapshot[cls_name] = round(float(np.mean(counts)), 1)
            if minute_snapshot:
                self._minute_series.append({"timestamp": now, "avgs": minute_snapshot})
            self._current_minute_data = {}
            self._last_minute_ts = now

        # Compute statistics
        total_detections = sum(self._class_counts.values())

        class_stats = {}
        for cls_name, count in sorted(self._class_counts.items(), key=lambda x: x[1], reverse=True):
            class_stats[cls_name] = {
                "total_detections": count,
                "pct_of_all": round(count / max(total_detections, 1) * 100, 1),
                "frames_present_pct": round(self._class_frame_counts.get(cls_name, 0) / max(self._total_frames, 1) * 100, 1),
                "unique_tracked": len(self._unique_by_class.get(cls_name, set())),
                "current_count": frame_class_counts.get(cls_name, 0),
            }

        stats = {
            "total_detections": total_detections,
            "total_frames_analyzed": self._total_frames,
            "distinct_classes": len(self._class_counts),
            "class_breakdown": class_stats,
            "top_5_classes": list(class_stats.keys())[:5],
            "minute_series": list(self._minute_series)[-10:],
        }

        self._display_data = stats
        return stats
