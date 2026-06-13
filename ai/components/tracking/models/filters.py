"""Anti-furniture filters and temporal confidence tracking."""

from collections import defaultdict

import cv2
import numpy as np

from ..config import Config


class PersonConfidenceTracker:
    """
    Gate that requires a YOLO track to survive N consecutive detections
    before treating it as a real person and extracting features.
    """

    def __init__(self, cfg: Config | None = None) -> None:
        if cfg is None:
            cfg = Config()
        self.n_confirm = cfg.n_confirm_frames
        self._counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    def tick(self, camera_id: str, track_id: int) -> bool:
        self._counts[camera_id][track_id] += 1
        return self._counts[camera_id][track_id] >= self.n_confirm

    def reset(self, camera_id: str, track_id: int) -> None:
        self._counts[camera_id].pop(track_id, None)

    def cleanup(self, camera_id: str, active_track_ids: set[int]) -> None:
        stale = [tid for tid in self._counts[camera_id] if tid not in active_track_ids]
        for tid in stale:
            del self._counts[camera_id][tid]


def is_valid_person_detection(
    x1: int, y1: int, x2: int, y2: int,
    crop: np.ndarray,
    cfg: Config | None = None,
) -> tuple[bool, str]:
    """
    Returns (True, "") if the crop is likely a person.
    Returns (False, reason) if rejected by geometry/luminance checks.
    """
    if cfg is None:
        cfg = Config()

    w = x2 - x1
    h = y2 - y1

    area = w * h
    if area < cfg.min_crop_area:
        return False, f"area too small ({area} < {cfg.min_crop_area})"

    if h < 80:
        return False, f"height too small ({h}px)"
    if w < 20:
        return False, f"width too small ({w}px)"

    aspect = h / max(w, 1)
    if aspect < cfg.min_aspect_ratio:
        return False, f"aspect ratio too low ({aspect:.2f} < {cfg.min_aspect_ratio})"

    if crop.size > 0:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        n_bands = 8
        band_h = max(1, gray.shape[0] // n_bands)
        band_means = [
            gray[i * band_h: (i + 1) * band_h, :].mean()
            for i in range(n_bands)
            if i * band_h < gray.shape[0]
        ]
        lum_var = float(np.var(band_means))
        if lum_var < cfg.min_luminance_variance:
            return False, f"luminance variance too low ({lum_var:.1f} < {cfg.min_luminance_variance})"

    return True, ""


def is_person_by_appearance(crop: np.ndarray, cfg: Config | None = None) -> tuple[bool, str]:
    """
    Clothing color variance check on the torso region.
    Returns (True, "") if crop passes, (False, reason) otherwise.
    """
    if cfg is None:
        cfg = Config()

    if crop.size == 0:
        return False, "empty crop"

    h = crop.shape[0]
    torso_top = int(h * 0.30)
    torso_bot = int(h * 0.70)
    torso = crop[torso_top:torso_bot, :]

    if torso.size == 0:
        return True, ""

    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
    sat_channel = hsv[:, :, 1].astype(np.float32)
    color_var = float(np.std(sat_channel))

    if color_var < cfg.min_color_variance:
        return False, f"color variance too low ({color_var:.1f} < {cfg.min_color_variance})"

    return True, ""
