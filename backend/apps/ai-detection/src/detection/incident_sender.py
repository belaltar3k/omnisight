from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class IncidentSender:
    """HTTP client that sends anomaly detections to incident-service edge endpoints."""

    def __init__(
        self,
        incident_service_url: str,
        edge_sync_secret: str,
        edge_node_code: str,
        timeout: float = 10.0,
    ):
        self.base_url = incident_service_url.rstrip("/")
        self.edge_sync_secret = edge_sync_secret
        self.edge_node_code = edge_node_code
        self._client = httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-edge-secret": self.edge_sync_secret,
        }

    def send_sync(
        self,
        camera_code: str,
        track_id: str,
        crime_type: str,
        confidence: float,
        detected_at: Optional[datetime] = None,
        ai_metadata: Optional[dict[str, Any]] = None,
        video_url: Optional[str] = None,
    ) -> Optional[dict]:
        if detected_at is None:
            detected_at = datetime.now(timezone.utc)

        detection: dict[str, Any] = {
            "cameraCode": camera_code,
            "trackId": track_id,
            "crimeType": crime_type,
            "confidence": round(confidence, 4),
            "detectedAt": detected_at.isoformat(),
            "modelVersion": "omnisight-ai-detection-v1.0",
            "aiMetadata": ai_metadata or {},
        }
        if video_url:
            detection["videoUrl"] = video_url

        payload = {
            "edgeNodeCode": self.edge_node_code,
            "detections": [detection],
        }

        try:
            resp = self._client.post(
                f"{self.base_url}/edge/sync",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "edge/sync sent for %s track=%s crime=%s conf=%.2f -> %s",
                camera_code, track_id, crime_type, confidence, result,
            )
            return result
        except httpx.HTTPStatusError as e:
            logger.error("edge/sync HTTP %s: %s", e.response.status_code, e.response.text)
        except Exception as e:
            logger.error("edge/sync failed: %s", e)
        return None

    def send_classify(
        self,
        track_id: str,
        crime_type: str,
        confidence: float,
        video_url: Optional[str] = None,
        vlm_verification: Optional[dict] = None,
    ) -> Optional[dict]:
        payload = {
            "trackId": track_id,
            "crimeType": crime_type,
            "confidence": round(confidence, 4),
        }
        if video_url:
            payload["videoUrl"] = video_url
        if vlm_verification:
            payload["vlmVerification"] = vlm_verification

        try:
            resp = self._client.post(
                f"{self.base_url}/edge/classify",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "edge/classify sent track=%s crime=%s conf=%.2f -> %s",
                track_id, crime_type, confidence, result,
            )
            return result
        except httpx.HTTPStatusError as e:
            logger.error("edge/classify HTTP %s: %s", e.response.status_code, e.response.text)
        except Exception as e:
            logger.error("edge/classify failed: %s", e)
        return None

    def close(self):
        self._client.close()
