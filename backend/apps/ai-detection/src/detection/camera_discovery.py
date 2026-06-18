from __future__ import annotations

import json
import logging
from typing import Optional

import redis

logger = logging.getLogger(__name__)


class CameraDiscovery:
    """Discovers active cameras by scanning Redis keys set by video-ingestion."""

    def __init__(self, redis_host: str, redis_port: int):
        self._client: Optional[redis.Redis] = None
        self._host = redis_host
        self._port = redis_port

    def connect(self) -> bool:
        try:
            self._client = redis.Redis(
                host=self._host, port=self._port, decode_responses=True
            )
            self._client.ping()
            logger.info("Connected to Redis at %s:%s for camera discovery", self._host, self._port)
            return True
        except Exception as e:
            logger.warning("Cannot connect to Redis for camera discovery: %s", e)
            self._client = None
            return False

    def discover(self) -> list[dict]:
        """
        Scan Redis for camera:status:* keys written by video-ingestion.
        Returns a list of dicts: [{camera_id, status, fps, ...}, ...]
        """
        if self._client is None:
            if not self.connect():
                return []

        cameras = []
        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match="camera:status:*", count=100)
                for key in keys:
                    camera_id = key.split("camera:status:")[-1]
                    try:
                        raw = self._client.get(key)
                        if raw:
                            data = json.loads(raw)
                            data["camera_id"] = camera_id
                            cameras.append(data)
                    except Exception:
                        cameras.append({"camera_id": camera_id, "status": "unknown"})
                if cursor == 0:
                    break
        except Exception as e:
            logger.error("Camera discovery scan failed: %s", e)

        return cameras

    def get_active_camera_ids(self) -> list[str]:
        cameras = self.discover()
        return [c["camera_id"] for c in cameras if c.get("status") == "online"]

    def close(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
