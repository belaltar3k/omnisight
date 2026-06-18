from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from src.core.config import Settings
from src.detection.frame_reader import SharedMemoryFrameReader, RTSPFrameReader
from src.detection.incident_sender import IncidentSender
from src.detection.model_manager import ModelManager
from src.detection.streaming_adapters.base import StreamingDetector
from src.detection.streaming_adapters.paan_streaming import PAANStreamingDetector
from src.detection.streaming_fusion import AnomalyState, StreamingFusionEngine
from src.detection.track_manager import TrackManager

logger = logging.getLogger(__name__)


class CameraPipeline:
    """
    Per-camera processing pipeline. Runs in a dedicated thread.
    Reads frames (from RTSP in native mode, or shared memory in Docker mode),
    dispatches to all active detectors, fuses scores, and sends incidents
    when anomalies are confirmed.
    """

    def __init__(
        self,
        camera_id: str,
        config: Settings,
        model_manager: ModelManager,
        incident_sender: IncidentSender,
        rtsp_url: str = "",
    ):
        self.camera_id = camera_id
        self.config = config
        self.model_manager = model_manager
        self.incident_sender = incident_sender
        self.rtsp_url = rtsp_url

        if config.MODE == "native" and rtsp_url:
            self.frame_reader = RTSPFrameReader(
                camera_id=camera_id,
                rtsp_url=rtsp_url,
                width=config.FRAME_WIDTH,
                height=config.FRAME_HEIGHT,
                target_fps=config.TARGET_FPS,
            )
        else:
            self.frame_reader = SharedMemoryFrameReader(
                camera_id=camera_id,
                ipc_prefix=config.IPC_PREFIX,
                width=config.FRAME_WIDTH,
                height=config.FRAME_HEIGHT,
            )

        self.fusion = StreamingFusionEngine(
            weights=config.get_weights_dict(),
            anomaly_threshold=config.ANOMALY_THRESHOLD,
            smoothing_window=config.SMOOTHING_WINDOW,
            dominance_weight=config.DOMINANCE_WEIGHT,
            min_anomaly_duration=config.MIN_ANOMALY_DURATION,
            cooldown_duration=config.ANOMALY_COOLDOWN,
        )
        self.track_manager = TrackManager(cooldown_seconds=60.0)

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._frame_count = 0
        self._fps = 0.0
        self._last_fused_score = 0.0
        self._status = "idle"
        self._total_detections_sent = 0
        self._last_sent_track_id: Optional[str] = None

        self._per_camera_detectors: dict[str, StreamingDetector] = {}

    @property
    def status(self) -> str:
        return self._status

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def last_fused_score(self) -> float:
        return self._last_fused_score

    @property
    def total_detections_sent(self) -> int:
        return self._total_detections_sent

    @property
    def active_detectors(self) -> list[str]:
        return list(self._per_camera_detectors.keys())

    def start(self):
        if self._running:
            return
        self._running = True
        self._status = "starting"
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"pipeline-{self.camera_id}")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=15)
        self.frame_reader.close()
        for det in self._per_camera_detectors.values():
            if hasattr(det, "stop"):
                det.stop()
        self._status = "stopped"

    def _run(self):
        logger.info("Camera pipeline starting for %s (mode=%s)", self.camera_id, self.config.MODE)

        if isinstance(self.frame_reader, RTSPFrameReader):
            self.frame_reader.start()
        self.frame_reader.wait_ready(timeout=120)

        self._init_per_camera_detectors()

        if paan := self._per_camera_detectors.get("paan"):
            if isinstance(paan, PAANStreamingDetector) and self.rtsp_url:
                paan.start_audio_capture(self.rtsp_url)

        self._status = "processing"
        sleep_interval = 1.0 / self.config.TARGET_FPS
        fps_timer = time.time()
        fps_frame_count = 0

        while self._running:
            try:
                frame = self.frame_reader.read()
                if frame is None:
                    time.sleep(0.1)
                    continue

                self._process_frame(frame)

                self._frame_count += 1
                fps_frame_count += 1

                elapsed = time.time() - fps_timer
                if elapsed >= 1.0:
                    self._fps = fps_frame_count / elapsed
                    fps_frame_count = 0
                    fps_timer = time.time()

                time.sleep(sleep_interval)

            except Exception as e:
                logger.error("Pipeline error for %s: %s", self.camera_id, e, exc_info=True)
                time.sleep(1)

        self._status = "stopped"
        logger.info("Camera pipeline stopped for %s", self.camera_id)

    def _init_per_camera_detectors(self):
        """
        Each camera gets its own detector instances because YOLO
        .track(persist=True) maintains per-sequence tracker state.
        """
        self._per_camera_detectors = self.model_manager.create_camera_detectors()

    def _process_frame(self, frame):
        timestamp = time.time()

        for name, detector in self._per_camera_detectors.items():
            try:
                result = detector.process_frame(frame, self._frame_count, timestamp)
                if result is not None:
                    self.fusion.push_score(name, result.score)
            except Exception as e:
                logger.error("Detector %s error on %s: %s", name, self.camera_id, e)

        if self._frame_count % self.config.FUSION_INTERVAL == 0:
            self._run_fusion(timestamp)

    def _run_fusion(self, timestamp: float):
        fused = self.fusion.fuse()
        self._last_fused_score = fused
        state, event = self.fusion.update_state(timestamp)

        if event is not None and state == AnomalyState.ANOMALOUS:
            self._dispatch_incident(event, timestamp)

    def _dispatch_incident(self, event, timestamp: float):
        skelnet_meta = {}
        videomae_meta = {}
        weapon_meta = {}

        skelnet = self._per_camera_detectors.get("crime_skelnet")
        if skelnet:
            skelnet_meta = skelnet.get_metadata()
        videomae = self._per_camera_detectors.get("video_mae")
        if videomae:
            videomae_meta = videomae.get_metadata()
        weapon = self._per_camera_detectors.get("weapon_detection")
        if weapon:
            weapon_meta = weapon.get_metadata()

        track_ids = skelnet_meta.get("track_ids", [])
        track_id = self.track_manager.generate_track_id(
            self.camera_id, track_ids, timestamp
        )

        if not self.track_manager.should_send(track_id):
            return

        weapon_detected = bool(weapon_meta.get("boxes"))
        crime_class_raw = videomae_meta.get("crime_class")
        skelnet_score = event.component_peaks.get("crime_skelnet", 0.0)

        crime_type = TrackManager.map_crime_class(
            videomae_class=crime_class_raw,
            weapon_detected=weapon_detected,
            skelnet_score=skelnet_score,
        )
        confidence = TrackManager.calculate_confidence(
            event.peak_score, event.component_peaks
        )

        ai_metadata = {
            "component_scores": event.component_peaks,
            "active_weights": dict(self.fusion.active_weights),
            "fused_peak": event.peak_score,
        }
        if weapon_meta.get("boxes"):
            ai_metadata["boundingBoxes"] = weapon_meta["boxes"]
        if track_ids:
            ai_metadata["keypoints"] = True

        sync_result = self.incident_sender.send_sync(
            camera_code=self.camera_id,
            track_id=track_id,
            crime_type=crime_type,
            confidence=confidence,
            ai_metadata=ai_metadata,
        )

        if sync_result:
            self.track_manager.mark_sent(track_id)
            self._total_detections_sent += 1
            self._last_sent_track_id = track_id

            self.incident_sender.send_classify(
                track_id=track_id,
                crime_type=crime_type,
                confidence=confidence,
            )
