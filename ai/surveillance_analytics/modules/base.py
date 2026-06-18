from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from surveillance_analytics.core.tracker import TrackInfo


class ModuleBase(ABC):
    NAME: str = "base"
    TIER: str = "fast"  # "fast" | "medium" | "slow" | "background"
    REQUIRES_MODEL: str = ""

    def __init__(self, config):
        self.config = config
        self._display_data: dict[str, Any] = {}
        self._alerts: list[dict[str, Any]] = []

    @abstractmethod
    def process(
        self,
        frame: np.ndarray,
        detections: list[dict],
        tracks: dict[int, TrackInfo],
    ) -> dict:
        ...

    def get_display_data(self) -> dict[str, Any]:
        return self._display_data

    def get_alerts(self) -> list[dict[str, Any]]:
        alerts = self._alerts.copy()
        self._alerts.clear()
        return alerts

    def is_available(self) -> bool:
        if self.REQUIRES_MODEL:
            return os.path.isfile(self.REQUIRES_MODEL)
        return True
