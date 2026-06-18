from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class TrackInfo:
    track_id: int
    class_id: int
    class_name: str
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    centroid: tuple[int, int]
    centroid_history: deque = field(default_factory=lambda: deque(maxlen=90))
    velocity_px: tuple[float, float] = (0.0, 0.0)
    speed_kmh: float = 0.0
    first_seen: float = 0.0
    last_seen: float = 0.0

    def __post_init__(self):
        if not self.first_seen:
            self.first_seen = time.time()
        self.last_seen = time.time()


VEHICLE_CLASS_IDS = {2, 3, 5, 7}  # car, motorcycle, bus, truck
PERSON_CLASS_ID = 0
COCO_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus",
    7: "truck", 24: "backpack", 25: "umbrella", 26: "handbag",
    28: "suitcase", 39: "bottle", 41: "cup",
}


class SmartCityTracker:
    def __init__(self, config):
        self.config = config
        self.tracks: dict[int, TrackInfo] = {}
        self._stale_timeout = 2.0

    def update(self, yolo_results) -> dict[int, TrackInfo]:
        now = time.time()
        seen_ids: set[int] = set()

        if yolo_results and yolo_results[0].boxes is not None:
            boxes = yolo_results[0].boxes
            has_ids = boxes.id is not None

            for i in range(len(boxes)):
                if not has_ids:
                    continue

                track_id = int(boxes.id[i].item())
                class_id = int(boxes.cls[i].item())
                x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().astype(int)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                seen_ids.add(track_id)

                if track_id in self.tracks:
                    t = self.tracks[track_id]
                    t.bbox = (int(x1), int(y1), int(x2), int(y2))
                    t.centroid = (cx, cy)
                    t.centroid_history.append((cx, cy))
                    t.class_id = class_id
                    t.last_seen = now
                    t.velocity_px = self._calc_velocity(t)
                    t.speed_kmh = self._calc_speed(t)
                else:
                    t = TrackInfo(
                        track_id=track_id,
                        class_id=class_id,
                        class_name=COCO_NAMES.get(class_id, f"cls_{class_id}"),
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        centroid=(cx, cy),
                        first_seen=now,
                        last_seen=now,
                    )
                    t.centroid_history.append((cx, cy))
                    self.tracks[track_id] = t

        stale = [
            tid for tid, t in self.tracks.items()
            if tid not in seen_ids and (now - t.last_seen) > self._stale_timeout
        ]
        for tid in stale:
            del self.tracks[tid]

        return self.tracks

    def _calc_velocity(self, track: TrackInfo) -> tuple[float, float]:
        h = track.centroid_history
        if len(h) < 2:
            return (0.0, 0.0)
        lookback = min(5, len(h))
        dx = h[-1][0] - h[-lookback][0]
        dy = h[-1][1] - h[-lookback][1]
        return (dx / lookback, dy / lookback)

    def _calc_speed(self, track: TrackInfo) -> float:
        vx, vy = track.velocity_px
        px_per_frame = math.hypot(vx, vy)
        px_per_sec = px_per_frame * self.config.camera_fps
        m_per_sec = px_per_sec / max(self.config.pixels_per_meter, 1e-6)
        return m_per_sec * 3.6

    def get_persons(self) -> dict[int, TrackInfo]:
        return {tid: t for tid, t in self.tracks.items() if t.class_id == PERSON_CLASS_ID}

    def get_vehicles(self) -> dict[int, TrackInfo]:
        return {tid: t for tid, t in self.tracks.items() if t.class_id in VEHICLE_CLASS_IDS}
