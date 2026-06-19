from __future__ import annotations

import base64
import io
import json
import logging
import os
import tempfile
import time
import uuid
from typing import TYPE_CHECKING, Optional

import cv2
import httpx
import numpy as np

if TYPE_CHECKING:
    from src.core.config import Settings
    from src.detection.incident_sender import IncidentSender

logger = logging.getLogger(__name__)

VALID_CRIME_TYPES = {
    "abnormal", "assault", "theft", "shoplifting",
    "vandalism", "fire", "weapon", "intrusion", "accident", "suspicious",
}


def _encode_frame(frame: np.ndarray, quality: int = 75) -> str:
    """Encode a BGR numpy frame as base64 JPEG."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _sample_frames(frames: list[np.ndarray], n: int) -> list[np.ndarray]:
    """Evenly sample N frames from a list."""
    if len(frames) <= n:
        return frames
    indices = [int(i * (len(frames) - 1) / (n - 1)) for i in range(n)]
    return [frames[i] for i in indices]


def _encode_to_mp4(frames: list[np.ndarray], fps: float = 5.0) -> Optional[bytes]:
    """Encode frames to an in-memory MP4 using a temp file."""
    if not frames:
        return None
    try:
        h, w = frames[0].shape[:2]
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp_path = tmp.name
        tmp.close()

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (w, h))
        for f in frames:
            writer.write(f)
        writer.release()

        with open(tmp_path, "rb") as fh:
            data = fh.read()
        os.unlink(tmp_path)
        return data
    except Exception as e:
        logger.warning("MP4 encoding failed: %s", e)
        return None


class VLMClient:
    """
    Sends anomaly frames to the remote VLM API (Qwen2.5-VL-7B-Instruct),
    uploads a video clip to S3, then updates the incident with the classified
    crime type and stores the full VLM analysis in analytics-service.
    """

    def __init__(self, config: "Settings"):
        self._vlm_url = (config.VLM_URL or "").rstrip("/")
        self._frames_sample = config.VLM_FRAMES_SAMPLE
        self._timeout = config.VLM_TIMEOUT
        self._analytics_url = config.ANALYTICS_SERVICE_URL.rstrip("/")

        self._s3_enabled = config.S3_ENABLED
        self._s3_bucket = config.S3_BUCKET
        self._s3_region = config.S3_REGION
        self._aws_key = config.AWS_ACCESS_KEY_ID
        self._aws_secret = config.AWS_SECRET_ACCESS_KEY

        self._s3 = None
        if self._s3_enabled and self._aws_key and self._aws_secret:
            try:
                import boto3
                self._s3 = boto3.client(
                    "s3",
                    region_name=self._s3_region,
                    aws_access_key_id=self._aws_key,
                    aws_secret_access_key=self._aws_secret,
                )
                logger.info("S3 client initialised (bucket=%s)", self._s3_bucket)
            except Exception as e:
                logger.warning("S3 init failed: %s", e)

    def is_enabled(self) -> bool:
        return bool(self._vlm_url)

    def analyze_and_update(
        self,
        frames: list[np.ndarray],
        track_id: str,
        camera_id: str,
        zone: str,
        fusion_score: float,
        incident_sender: "IncidentSender",
    ):
        """Runs in a background thread. Full pipeline: VLM → S3 → classify → analytics."""
        event_id = str(uuid.uuid4())
        timestamp = time.time()

        # 1. Upload video clip to S3
        video_url: Optional[str] = None
        if self._s3 and frames:
            video_url = self._upload_clip(frames, camera_id, event_id)

        # 2. Call VLM API
        vlm_result = self._call_vlm(frames, camera_id, zone, fusion_score, event_id, video_url)
        if vlm_result is None:
            logger.warning("VLM returned no result for track=%s — keeping 'abnormal'", track_id)
            return

        # 3. Update incident with VLM crime type
        crime_type = vlm_result.get("crime_type", "abnormal")
        if crime_type not in VALID_CRIME_TYPES:
            crime_type = "suspicious"
        vlm_confidence = 0.7  # VLM gives qualitative score; map to numeric

        classify_result = incident_sender.send_classify(
            track_id=track_id,
            crime_type=crime_type,
            confidence=vlm_confidence,
        )
        logger.info("VLM classify result for track=%s: crime=%s classify=%s", track_id, crime_type, classify_result)

        # 4. Store full VLM analysis in analytics-service
        self._ingest_to_analytics(
            track_id=track_id,
            camera_id=camera_id,
            zone=zone,
            vlm_result=vlm_result,
            video_url=video_url,
        )

    def _call_vlm(
        self,
        frames: list[np.ndarray],
        camera_id: str,
        zone: str,
        fusion_score: float,
        event_id: str,
        video_url: Optional[str],
    ) -> Optional[dict]:
        if not self._vlm_url:
            return None

        sampled = _sample_frames(frames, self._frames_sample)
        encoded = [_encode_frame(f) for f in sampled]

        payload = {
            "event_id": event_id,
            "camera_id": camera_id,
            "zone": zone,
            "anomaly_score_fusion": round(fusion_score, 4),
            "frames": encoded,
        }
        if video_url:
            payload["video_url"] = video_url

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self._vlm_url}/analyze", json=payload)
                resp.raise_for_status()
                result = resp.json()
                logger.info("VLM response for event=%s: %s", event_id,
                            {k: v for k, v in result.items() if k != "raw_vlm_output"})
                return result
        except httpx.HTTPStatusError as e:
            logger.error("VLM API HTTP %s: %s", e.response.status_code, e.response.text[:300])
        except Exception as e:
            logger.error("VLM API call failed: %s", e)
        return None

    def _upload_clip(self, frames: list[np.ndarray], camera_id: str, event_id: str) -> Optional[str]:
        """Encode frames to MP4 and upload to S3. Returns pre-signed URL or None."""
        mp4_bytes = _encode_to_mp4(frames, fps=5.0)
        if not mp4_bytes:
            return None

        key = f"clips/{camera_id}/{event_id}.mp4"
        try:
            self._s3.put_object(
                Bucket=self._s3_bucket,
                Key=key,
                Body=mp4_bytes,
                ContentType="video/mp4",
            )
            url = self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._s3_bucket, "Key": key},
                ExpiresIn=7 * 24 * 3600,
            )
            logger.info("Clip uploaded to S3: %s", key)
            return url
        except Exception as e:
            logger.warning("S3 upload failed: %s", e)
            return None

    def _ingest_to_analytics(
        self,
        track_id: str,
        camera_id: str,
        zone: str,
        vlm_result: dict,
        video_url: Optional[str],
    ):
        payload = {
            "track_id": track_id,
            "camera_id": camera_id,
            "zone": zone,
            "crime_type": vlm_result.get("crime_type", "abnormal"),
            "vlm_score": vlm_result.get("anomaly_score_vlm", "MEDIUM"),
            "people_count": vlm_result.get("people_count", 0),
            "caption": vlm_result.get("caption", ""),
            "events": vlm_result.get("observed_events", []),
            "evidence": vlm_result.get("anomaly_evidence", []),
            "video_url": video_url or "",
            "full_json": vlm_result,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self._analytics_url}/api/v1/analytics/vlm/ingest",
                    json=payload,
                )
                resp.raise_for_status()
                logger.debug("VLM analysis ingested to analytics-service for track=%s", track_id)
        except Exception as e:
            logger.warning("VLM analytics ingest failed: %s", e)
