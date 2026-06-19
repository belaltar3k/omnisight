from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)


def _sanitize(obj):
    """Recursively convert numpy types to native Python so httpx can JSON-encode them."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


class SurveillanceReporter:
    """
    Periodically batches surveillance analytics stats from the SA module
    and POSTs them to the analytics service as time-series snapshots.
    """

    def __init__(self, analytics_service_url: str, camera_id: str, interval: float = 30.0):
        self._url = analytics_service_url.rstrip("/") + "/api/v1/analytics/surveillance/ingest"
        self._camera_id = camera_id
        self._interval = interval
        self._latest_stats: Optional[dict] = None
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=10.0)
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name=f"sa-reporter-{self._camera_id}")
        self._thread.start()

    def stop(self):
        self._running = False
        self._client.close()

    def update(self, stats: dict):
        with self._lock:
            self._latest_stats = stats

    def _loop(self):
        while self._running:
            time.sleep(self._interval)
            with self._lock:
                stats = dict(self._latest_stats) if self._latest_stats else None
            if stats:
                self._send(stats)

    def _send(self, stats: dict):
        clean = _sanitize(stats)
        payload = {
            "camera_id": self._camera_id,
            "persons": int(clean.get("persons", 0)),
            "vehicles": int(clean.get("vehicles", 0)),
            "total_alerts": int(clean.get("total_alerts", 0)),
            "modules": {k: v for k, v in clean.items() if k not in ("persons", "vehicles", "total_alerts")},
        }
        try:
            resp = self._client.post(self._url, json=payload)
            resp.raise_for_status()
            logger.debug("SA metrics sent for %s", self._camera_id)
        except Exception as e:
            logger.warning("SA reporter failed for %s: %s", self._camera_id, e)
