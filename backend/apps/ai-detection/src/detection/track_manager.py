from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

CRIME_CLASS_MAP = {
    "Assault": "assault",
    "Fighting": "assault",
    "Abuse": "suspicious",
    "Arrest": "suspicious",
    "Arson": "fire",
    "Explosion": "fire",
    "Shooting": "weapon",
    "Robbery": "theft",
    "Burglary": "theft",
    "Stealing": "theft",
    "Shoplifting": "shoplifting",
    "Vandalism": "vandalism",
    "RoadAccidents": "accident",
    "Normal": "abnormal",
}


class TrackManager:
    """
    Generates trackIds for incident-service deduplication.
    Uses skeleton tracker IDs when available, otherwise synthetic IDs.
    Maintains cooldown to avoid re-sending the same track.
    """

    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self._sent_tracks: dict[str, float] = {}

    def generate_track_id(
        self,
        camera_id: str,
        skeleton_track_ids: list[int] | None = None,
        timestamp: float | None = None,
    ) -> str:
        ts = int((timestamp or time.time()) * 1000)
        if skeleton_track_ids:
            primary_id = skeleton_track_ids[0]
            return f"{camera_id}_track-{primary_id}_{ts}"
        return f"{camera_id}_anomaly_{ts}"

    def should_send(self, track_id: str) -> bool:
        now = time.time()
        self._cleanup(now)

        base = self._base_track(track_id)
        if base in self._sent_tracks:
            return False
        return True

    def mark_sent(self, track_id: str):
        self._sent_tracks[self._base_track(track_id)] = time.time()

    def _base_track(self, track_id: str) -> str:
        parts = track_id.rsplit("_", 1)
        return parts[0] if len(parts) > 1 else track_id

    def _cleanup(self, now: float):
        expired = [
            k for k, t in self._sent_tracks.items()
            if now - t > self.cooldown_seconds
        ]
        for k in expired:
            del self._sent_tracks[k]

    @staticmethod
    def map_crime_class(
        videomae_class: str | None = None,
        weapon_detected: bool = False,
        skelnet_score: float = 0.0,
    ) -> str:
        if weapon_detected:
            return "weapon"
        if videomae_class and videomae_class != "Normal":
            return CRIME_CLASS_MAP.get(videomae_class, "abnormal")
        if skelnet_score > 0.7:
            return "assault"
        return "abnormal"

    @staticmethod
    def calculate_confidence(
        fused_score: float,
        component_peaks: dict[str, float],
    ) -> float:
        if component_peaks:
            peak = max(component_peaks.values())
            return max(fused_score, peak)
        return fused_score
