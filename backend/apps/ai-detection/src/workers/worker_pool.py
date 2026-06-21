from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from src.core.config import Settings
from src.detection.camera_discovery import CameraDiscovery
from src.detection.incident_sender import IncidentSender
from src.detection.model_manager import ModelManager
from src.workers.camera_pipeline import CameraPipeline

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Manages per-camera CameraPipeline workers.

    In native mode: creates pipelines directly from RTSP_URLS on start.
    In docker mode: periodically discovers cameras from Redis and starts pipelines.
    """

    def __init__(
        self,
        config: Settings,
        model_manager: ModelManager,
        incident_sender: IncidentSender,
    ):
        self.config = config
        self.model_manager = model_manager
        self.incident_sender = incident_sender

        self._pipelines: dict[str, CameraPipeline] = {}
        self._discovery_thread: Optional[threading.Thread] = None
        self._running = False

        self._rtsp_map: dict[str, str] = {}
        if config.RTSP_URLS:
            for i, url in enumerate(config.RTSP_URLS):
                cam_id = f"cam-{i + 1:03d}"
                self._rtsp_map[cam_id] = url

    def start(self):
        self._running = True

        if self.config.MODE == "native":
            self._start_native()
        else:
            self._start_docker()

    def _start_native(self):
        if not self._rtsp_map:
            logger.warning("Native mode but no RTSP_URLS configured — no cameras to process")
            return

        logger.info("Native mode: starting %d pipeline(s) from RTSP_URLS", len(self._rtsp_map))
        for cam_id, rtsp_url in self._rtsp_map.items():
            self._create_pipeline(cam_id, rtsp_url)

        self._discovery_thread = threading.Thread(
            target=self._native_discovery_loop, daemon=True, name="native-discovery"
        )
        self._discovery_thread.start()

    def _native_discovery_loop(self):
        """
        In native mode, also try Redis discovery as a fallback.
        video-ingestion writes camera:status:* keys — if those appear,
        start pipelines for any cameras not already running.
        """
        discovery = CameraDiscovery(self.config.REDIS_HOST, self.config.REDIS_PORT)
        if not discovery.connect():
            logger.info("Redis not available in native mode — using RTSP_URLS only")
            return

        while self._running:
            try:
                camera_ids = discovery.get_active_camera_ids()
                for cam_id in camera_ids:
                    if cam_id not in self._pipelines:
                        rtsp_url = self._rtsp_map.get(cam_id, "")
                        if rtsp_url:
                            logger.info("Redis discovered camera %s — starting pipeline", cam_id)
                            self._create_pipeline(cam_id, rtsp_url)
            except Exception as e:
                logger.debug("Native Redis discovery error (non-critical): %s", e)
            time.sleep(self.config.CAMERA_DISCOVERY_INTERVAL)

        discovery.close()

    def _start_docker(self):
        discovery = CameraDiscovery(self.config.REDIS_HOST, self.config.REDIS_PORT)
        discovery.connect()
        self._docker_discovery = discovery

        self._discovery_thread = threading.Thread(
            target=self._docker_discovery_loop, daemon=True, name="camera-discovery"
        )
        self._discovery_thread.start()

    def _docker_discovery_loop(self):
        logger.info("Docker mode: camera discovery loop started (interval=%ds)", self.config.CAMERA_DISCOVERY_INTERVAL)
        while self._running:
            try:
                camera_ids = self._docker_discovery.get_active_camera_ids()
                for cam_id in camera_ids:
                    if cam_id not in self._pipelines:
                        logger.info("Discovered new camera: %s — starting pipeline", cam_id)
                        rtsp_url = self._rtsp_map.get(cam_id, "")
                        self._create_pipeline(cam_id, rtsp_url)
            except Exception as e:
                logger.error("Camera discovery error: %s", e)
            time.sleep(self.config.CAMERA_DISCOVERY_INTERVAL)

    def _create_pipeline(self, cam_id: str, rtsp_url: str):
        pipeline = CameraPipeline(
            camera_id=cam_id,
            config=self.config,
            model_manager=self.model_manager,
            incident_sender=self.incident_sender,
            rtsp_url=rtsp_url,
        )
        pipeline.start()
        self._pipelines[cam_id] = pipeline

    def stop(self):
        self._running = False
        for cam_id, pipeline in self._pipelines.items():
            logger.info("Stopping pipeline for %s", cam_id)
            pipeline.stop()
        self._pipelines.clear()
        if hasattr(self, "_docker_discovery"):
            self._docker_discovery.close()
        if self._discovery_thread:
            self._discovery_thread.join(timeout=15)

    def get_pipeline(self, camera_id: str) -> Optional[CameraPipeline]:
        return self._pipelines.get(camera_id)

    def get_all_status(self) -> list[dict]:
        result = []
        for cam_id, pipeline in self._pipelines.items():
            result.append({
                "camera_id": cam_id,
                "status": pipeline.status,
                "fps": round(pipeline.fps, 1),
                "active_detectors": pipeline.active_detectors,
                "last_fusion_score": round(pipeline.last_fused_score, 4),
                "anomaly_active": pipeline.is_anomaly_active,
                "total_detections_sent": pipeline.total_detections_sent,
            })
        return result
