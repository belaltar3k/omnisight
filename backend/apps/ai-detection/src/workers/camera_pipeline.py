from __future__ import annotations

import collections
import concurrent.futures
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
from src.detection.surveillance_reporter import SurveillanceReporter
from src.detection.vlm_client import VLMClient

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
            max_anomaly_duration=config.MAX_ANOMALY_DURATION,
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

        self._latest_frame: Optional[np.ndarray] = None
        self._latest_meta: dict = {}
        self._frame_lock = threading.Lock()

        self._sa_reporter = SurveillanceReporter(
            analytics_service_url=config.ANALYTICS_SERVICE_URL,
            camera_id=camera_id,
            interval=30.0,
        )

        # Frame buffer: collect frames during WARMING + ANOMALOUS for VLM analysis
        # maxlen caps memory; at 15 fps this is ~8 seconds of footage
        self._frame_buffer: collections.deque = collections.deque(maxlen=120)

        self._vlm_client = VLMClient(config) if config.VLM_URL else None
        self._vlm_executor: Optional[concurrent.futures.ThreadPoolExecutor] = (
            concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="vlm")
            if self._vlm_client
            else None
        )

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
        self._sa_reporter.stop()
        if self._vlm_executor:
            self._vlm_executor.shutdown(wait=False)
        self._status = "stopped"

    def _run(self):
        logger.info("Camera pipeline starting for %s (mode=%s)", self.camera_id, self.config.MODE)

        if isinstance(self.frame_reader, RTSPFrameReader):
            self.frame_reader.start()
        self.frame_reader.wait_ready(timeout=120)

        self._init_per_camera_detectors()
        self._sa_reporter.start()

        if paan := self._per_camera_detectors.get("paan"):
            if isinstance(paan, PAANStreamingDetector) and self.rtsp_url:
                paan.start_audio_capture(self.rtsp_url)

        self._status = "processing"
        target_interval = 1.0 / self.config.TARGET_FPS
        fps_timer = time.time()
        fps_frame_count = 0

        while self._running:
            try:
                t0 = time.time()

                frame = self.frame_reader.read()
                if frame is None:
                    time.sleep(0.01)
                    continue

                self._process_frame(frame)

                self._frame_count += 1
                fps_frame_count += 1

                elapsed = time.time() - fps_timer
                if elapsed >= 1.0:
                    self._fps = fps_frame_count / elapsed
                    fps_frame_count = 0
                    fps_timer = time.time()

                # Only sleep the time remaining in the target interval.
                # If inference already took longer than target_interval, skip the sleep.
                remaining = target_interval - (time.time() - t0)
                if remaining > 0:
                    time.sleep(remaining)

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

    def get_stream_frame(self) -> Optional[bytes]:
        import cv2
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            frame = self._latest_frame.copy()
            meta = dict(self._latest_meta)

        score = meta.get("fusion_score", 0.0)
        anomaly = meta.get("anomaly_active", False)
        component_scores = meta.get("component_scores", {})
        bboxes = meta.get("bboxes", {})

        h, w = frame.shape[:2]

        # border colour: red if anomalous, green otherwise
        border_color = (0, 0, 220) if anomaly else (0, 180, 0)
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), border_color, 6)

        # fusion score bar along the top
        bar_w = int(w * score)
        bar_color = (0, 0, 220) if score > 0.55 else (0, 200, 80)
        cv2.rectangle(frame, (0, 0), (bar_w, 8), bar_color, -1)
        cv2.rectangle(frame, (0, 0), (w, 8), (60, 60, 60), 1)

        # overlay text
        def text(img, msg, y, color=(255, 255, 255)):
            cv2.putText(img, msg, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(img, msg, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color,   1, cv2.LINE_AA)

        state_label = "ANOMALY" if anomaly else "NORMAL"
        state_color = (0, 0, 220) if anomaly else (0, 220, 0)
        text(frame, f"Score: {score:.3f}  [{state_label}]", 35, state_color)

        y = 58
        for name, s in component_scores.items():
            text(frame, f"  {name}: {s:.3f}", y)
            y += 20

        text(frame, f"FPS: {meta.get('fps', 0):.1f}  cam: {self.camera_id}", h - 12)

        # skeleton bounding boxes (from crime_skelnet)
        for track_id, xyxy in bboxes.items():
            x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
            cv2.putText(frame, f"#{track_id}", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1, cv2.LINE_AA)

        _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return jpg.tobytes()

    def _process_frame(self, frame):
        timestamp = time.time()
        detector_scores: dict[str, float] = {}
        all_bboxes: dict[int, "np.ndarray"] = {}

        for name, detector in self._per_camera_detectors.items():
            try:
                result = detector.process_frame(frame, self._frame_count, timestamp)
                if result is not None:
                    self.fusion.push_score(name, result.score)
                    detector_scores[name] = result.score
                    if name == "crime_skelnet":
                        all_bboxes.update(result.metadata.get("bboxes", {}))
                    elif name == "surveillance_analytics":
                        sa_stats = result.metadata.get("stats", {})
                        if sa_stats:
                            self._sa_reporter.update(sa_stats)
            except Exception as e:
                logger.error("Detector %s error on %s: %s", name, self.camera_id, e)

        with self._frame_lock:
            self._latest_frame = frame.copy()
            self._latest_meta = {
                "fusion_score": self._last_fused_score,
                "anomaly_active": self.fusion.state.value != "normal",
                "component_scores": detector_scores,
                "bboxes": all_bboxes,
                "fps": self._fps,
            }

        # Buffer frames during suspicious/anomalous states for VLM clip
        if self._vlm_client and self.fusion.state in (AnomalyState.WARMING, AnomalyState.ANOMALOUS):
            self._frame_buffer.append(frame)

        if self._frame_count % self.config.FUSION_INTERVAL == 0:
            self._run_fusion(timestamp)

    def _run_fusion(self, timestamp: float):
        fused = self.fusion.fuse()
        self._last_fused_score = fused
        prev_state = self.fusion.state
        state, event = self.fusion.update_state(timestamp)

        # When leaving ANOMALOUS, reset the skelnet buffer so accumulated scores
        # from the completed anomaly don't bleed into the next WARMING window.
        if prev_state == AnomalyState.ANOMALOUS and state == AnomalyState.COOLDOWN:
            skelnet = self._per_camera_detectors.get("crime_skelnet")
            if skelnet and hasattr(skelnet, "reset"):
                skelnet.reset()

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

            if self._vlm_client and self._vlm_executor:
                # VLM runs in background: classifies crime type, uploads clip, updates incident
                clip_frames = list(self._frame_buffer)
                self._frame_buffer.clear()
                self._vlm_executor.submit(
                    self._vlm_client.analyze_and_update,
                    frames=clip_frames,
                    track_id=track_id,
                    camera_id=self.camera_id,
                    zone="",
                    fusion_score=event.peak_score,
                    incident_sender=self.incident_sender,
                )
            else:
                # No VLM configured: keep crime_type=abnormal, no reclassification
                self._frame_buffer.clear()
