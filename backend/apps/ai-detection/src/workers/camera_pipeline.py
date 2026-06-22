from __future__ import annotations

import collections
import concurrent.futures
import logging
import os
import queue
import sys
import tempfile
import threading
import time
import uuid
from typing import Optional

import cv2
import numpy as np

from src.core.config import Settings
from src.detection.frame_reader import SharedMemoryFrameReader, RTSPFrameReader
from src.detection.incident_sender import IncidentSender
from src.detection.model_manager import ModelManager, _ensure_ai_path
from src.detection.track_manager import TrackManager
from src.detection.surveillance_reporter import SurveillanceReporter
from src.detection.vlm_client import VLMClient, _encode_to_mp4

logger = logging.getLogger(__name__)


class CameraPipeline:
    """
    Per-camera processing pipeline using micro-batch inference.

    Accumulates MICRO_BATCH_SECONDS of frames, writes them to a temp video,
    runs all enabled batch detectors on that clip, fuses scores, and dispatches
    incidents when an anomaly is detected. Surveillance analytics and PAAN audio
    continue to run in their original streaming/threaded modes since they don't
    require video-file context.
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

        self.track_manager = TrackManager(cooldown_seconds=60.0)

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._frame_count = 0
        self._fps = 0.0
        self._last_fused_score = 0.0
        self._is_anomaly_active = False
        self._status = "idle"
        self._total_detections_sent = 0
        self._last_sent_track_id: Optional[str] = None

        # Per-camera detector instances (created at _run() time)
        self._batch_detectors: dict = {}
        self._paan_detector = None
        self._sa_detector = None

        self._latest_frame: Optional[np.ndarray] = None
        self._latest_meta: dict = {}
        self._frame_lock = threading.Lock()

        self._sa_reporter = SurveillanceReporter(
            analytics_service_url=config.ANALYTICS_SERVICE_URL,
            camera_id=camera_id,
            interval=30.0,
        )

        # Micro-batch frame accumulation
        self._micro_batch_frames: list[np.ndarray] = []
        self._micro_batch_target = max(1, int(config.MICRO_BATCH_SECONDS * config.TARGET_FPS))

        # Cooldown: don't dispatch incidents faster than this
        self._last_dispatch_time: float = 0.0

        # Runtime-adjustable settings (updated via API)
        self._anomaly_threshold = config.ANOMALY_THRESHOLD
        self._weights: dict[str, float] = config.get_weights_dict()

        # Replay queue: annotated JPEG bytes from completed micro-batches.
        # The stream endpoint consumes these in order so the viewer sees
        # each processed clip played back frame-by-frame with detection overlays.
        # maxsize caps at ~6 batches of frames to bound memory.
        self._replay_queue: queue.Queue = queue.Queue(
            maxsize=self._micro_batch_target * 6
        )
        self._last_replay_frame: Optional[bytes] = None

        # VLM clip buffer (last N frames before dispatch)
        self._vlm_frame_buffer: list[np.ndarray] = []
        self._vlm_client = VLMClient(config) if config.VLM_URL else None
        self._vlm_executor: Optional[concurrent.futures.ThreadPoolExecutor] = (
            concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="vlm")
            if self._vlm_client
            else None
        )

        # S3 client — initialized independently so clips upload even without VLM
        self._s3: Optional[object] = None
        self._s3_bucket = config.S3_BUCKET
        self._s3_region = config.S3_REGION
        if config.S3_ENABLED and config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            try:
                import boto3
                self._s3 = boto3.client(
                    "s3",
                    region_name=config.S3_REGION,
                    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                )
                logger.info("S3 client initialised for camera %s (bucket=%s)", camera_id, config.S3_BUCKET)
            except Exception as e:
                logger.warning("S3 init failed for camera %s: %s", camera_id, e)

    # ------------------------------------------------------------------
    # Properties (consumed by WorkerPool and API routes)
    # ------------------------------------------------------------------

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
    def is_anomaly_active(self) -> bool:
        return self._is_anomaly_active

    @property
    def total_detections_sent(self) -> int:
        return self._total_detections_sent

    @property
    def active_detectors(self) -> list[str]:
        names = list(self._batch_detectors.keys())
        if self._paan_detector is not None:
            names.append("paan")
        if self._sa_detector is not None:
            names.append("surveillance_analytics")
        return names

    def update_weights(self, weights: dict[str, float]):
        self._weights = dict(weights)

    def update_anomaly_threshold(self, threshold: float):
        self._anomaly_threshold = threshold

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._running:
            return
        self._running = True
        self._status = "starting"
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"pipeline-{self.camera_id}"
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=15)
        self.frame_reader.close()
        if self._paan_detector is not None and hasattr(self._paan_detector, "stop"):
            self._paan_detector.stop()
        self._sa_reporter.stop()
        if self._vlm_executor:
            self._vlm_executor.shutdown(wait=False)
        self._status = "stopped"

    def _run(self):
        logger.info(
            "Camera pipeline starting for %s (mode=%s, batch=%.1fs @ %dfps = %d frames)",
            self.camera_id, self.config.MODE,
            self.config.MICRO_BATCH_SECONDS, self.config.TARGET_FPS,
            self._micro_batch_target,
        )

        if isinstance(self.frame_reader, RTSPFrameReader):
            self.frame_reader.start()
        self.frame_reader.wait_ready(timeout=120)

        self._init_detectors()
        self._sa_reporter.start()

        if self._paan_detector is not None and self.rtsp_url:
            self._paan_detector.start_audio_capture(self.rtsp_url)

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

                self._accumulate_frame(frame)

                self._frame_count += 1
                fps_frame_count += 1

                elapsed = time.time() - fps_timer
                if elapsed >= 1.0:
                    self._fps = fps_frame_count / elapsed
                    fps_frame_count = 0
                    fps_timer = time.time()

                remaining = target_interval - (time.time() - t0)
                if remaining > 0:
                    time.sleep(remaining)

            except Exception as e:
                logger.error(
                    "Pipeline error for %s: %s", self.camera_id, e, exc_info=True
                )
                time.sleep(1)

        self._status = "stopped"
        logger.info("Camera pipeline stopped for %s", self.camera_id)

    def _init_detectors(self):
        self._batch_detectors = self.model_manager.create_camera_batch_detectors()
        self._paan_detector = self.model_manager.create_paan_detector()
        self._sa_detector = self.model_manager.create_sa_detector()

    # ------------------------------------------------------------------
    # Frame accumulation
    # ------------------------------------------------------------------

    def _accumulate_frame(self, frame: np.ndarray):
        timestamp = time.time()

        # Surveillance analytics runs per-frame for crowd stats (score always 0.0)
        if self._sa_detector is not None:
            try:
                sa_result = self._sa_detector.process_frame(
                    frame, self._frame_count, timestamp
                )
                if sa_result is not None:
                    stats = sa_result.metadata.get("stats", {})
                    if stats:
                        self._sa_reporter.update(stats)
            except Exception as e:
                logger.error("SurveillanceAnalytics error on %s: %s", self.camera_id, e)

        self._micro_batch_frames.append(frame.copy())

        # Update the live preview frame
        with self._frame_lock:
            self._latest_frame = frame.copy()
            self._latest_meta = {
                "fusion_score": self._last_fused_score,
                "anomaly_active": self._is_anomaly_active,
                "component_scores": self._latest_meta.get("component_scores", {}),
                "bboxes": self._latest_meta.get("bboxes", {}),
                "fps": self._fps,
            }

        if len(self._micro_batch_frames) >= self._micro_batch_target:
            batch = self._micro_batch_frames
            self._micro_batch_frames = []
            self._process_micro_batch(batch)

    # ------------------------------------------------------------------
    # Micro-batch inference
    # ------------------------------------------------------------------

    def _process_micro_batch(self, frames: list[np.ndarray]):
        if not frames or not self._batch_detectors:
            return

        logger.info(
            "[%s] Processing micro-batch: %d frames", self.camera_id, len(frames)
        )

        tmp_path = self._write_temp_video(frames)
        if tmp_path is None:
            return

        try:
            _ensure_ai_path()
            from pipeline.base import DetectorResult
            from pipeline.fusion import WeightedFusionEngine

            total_frames = len(frames)
            results: dict[str, DetectorResult] = {}

            for name, det in self._batch_detectors.items():
                try:
                    t0 = time.time()
                    result = det.predict(tmp_path, total_frames=total_frames)
                    elapsed = time.time() - t0
                    if result is not None:
                        results[name] = result
                        peak = float(result.scores.max()) if len(result.scores) > 0 else 0.0
                        logger.info(
                            "[%s] %s done in %.1fs (peak=%.3f)",
                            self.camera_id, name, elapsed, peak,
                        )
                    else:
                        logger.info(
                            "[%s] %s returned None in %.1fs", self.camera_id, name, elapsed
                        )
                except Exception as e:
                    logger.error(
                        "Batch detector %s error on %s: %s", name, self.camera_id, e,
                        exc_info=True,
                    )

            # Capture PAAN score separately — it is an additive audio boost,
            # not a weighted-pool participant, so crime_skelnet and weapon_detection
            # weights stay exactly as configured regardless of whether audio fires.
            paan_boost_scores = None
            if self._paan_detector is not None:
                paan_score = self._paan_detector._score
                if paan_score > 0.0:
                    paan_boost_scores = np.full(total_frames, paan_score, dtype=np.float32)

            if not results:
                logger.warning("[%s] No detector results for this batch", self.camera_id)
                return

            # No smoothing here: SkelNet and VideoMAE already do temporal windowing
            # inside their own inference, so applying a moving-average on top dilutes
            # brief high-score peaks and raises the effective detection threshold.
            fusion = WeightedFusionEngine(
                weights=self._weights,
                anomaly_threshold=self._anomaly_threshold,
                smoothing_window=1,
                dominance_weight=self.config.DOMINANCE_WEIGHT,
            )
            pipeline_result = fusion.fuse(
                results,
                num_frames=total_frames,
                fps=float(self.config.TARGET_FPS),
                processing_time=0.0,
                audio_boost_scores=paan_boost_scores,
                audio_boost_strength=self.config.PAAN_BOOST_STRENGTH,
            )

            self._last_fused_score = pipeline_result.peak_score
            self._is_anomaly_active = pipeline_result.is_anomalous

            component_scores = {
                name: float(r.scores.mean()) if len(r.scores) > 0 else 0.0
                for name, r in results.items()
            }
            skelnet_result = results.get("crime_skelnet")
            bboxes = {}
            if skelnet_result:
                frame_bboxes = skelnet_result.metadata.get("frame_bboxes", [])
                if frame_bboxes:
                    bboxes = frame_bboxes[-1] if frame_bboxes else {}

            with self._frame_lock:
                self._latest_meta.update({
                    "fusion_score": pipeline_result.peak_score,
                    "anomaly_active": pipeline_result.is_anomalous,
                    "component_scores": component_scores,
                    "bboxes": bboxes,
                })

            logger.info(
                "[%s] Fusion: peak=%.3f  anomalous=%s  regions=%d",
                self.camera_id,
                pipeline_result.peak_score,
                pipeline_result.is_anomalous,
                len(pipeline_result.anomaly_regions),
            )

            if pipeline_result.is_anomalous:
                cooldown_elapsed = time.time() - self._last_dispatch_time
                if cooldown_elapsed >= self.config.ANOMALY_COOLDOWN:
                    self._dispatch_incident(pipeline_result, results, frames)

            # Annotate every frame in the batch with per-frame results and
            # push them to the replay queue so the stream endpoint can serve them.
            self._push_batch_to_replay(frames, pipeline_result, results)

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _push_batch_to_replay(self, frames, pipeline_result, results):
        """Annotate every frame in the batch and push to the replay queue."""
        skelnet_result = results.get("crime_skelnet")
        frame_bboxes_list = (
            skelnet_result.metadata.get("frame_bboxes", []) if skelnet_result else []
        )

        total = len(frames)
        for i, frame in enumerate(frames):
            # Per-frame fused score from the fusion result
            frame_score = float(pipeline_result.fused_scores[i]) if i < len(pipeline_result.fused_scores) else pipeline_result.peak_score
            frame_anomalous = bool(pipeline_result.anomaly_mask[i]) if i < len(pipeline_result.anomaly_mask) else pipeline_result.is_anomalous

            # Per-component scores at this frame index
            component_scores: dict[str, float] = {}
            for name, score_arr in pipeline_result.component_scores.items():
                if len(score_arr) > 0:
                    idx = min(i, len(score_arr) - 1)
                    component_scores[name] = float(score_arr[idx])

            # Bounding boxes from SkelNet at this frame
            bboxes: dict = {}
            if frame_bboxes_list and i < len(frame_bboxes_list):
                bboxes = frame_bboxes_list[i]

            jpg = self._render_frame(frame, frame_score, frame_anomalous, component_scores, bboxes, i, total)
            if jpg is not None:
                try:
                    self._replay_queue.put_nowait(jpg)
                except queue.Full:
                    # Drop oldest frame to make room
                    try:
                        self._replay_queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._replay_queue.put_nowait(jpg)
                    except queue.Full:
                        pass

    def _render_frame(
        self,
        frame: np.ndarray,
        score: float,
        anomalous: bool,
        component_scores: dict[str, float],
        bboxes: dict,
        frame_idx: int,
        total_frames: int,
    ) -> Optional[bytes]:
        img = frame.copy()
        h, w = img.shape[:2]

        border_color = (0, 0, 220) if anomalous else (0, 180, 0)
        cv2.rectangle(img, (0, 0), (w - 1, h - 1), border_color, 6)

        # Score bar along the top
        bar_w = int(w * score)
        bar_color = (0, 0, 220) if score > self._anomaly_threshold else (0, 200, 80)
        cv2.rectangle(img, (0, 0), (bar_w, 8), bar_color, -1)
        cv2.rectangle(img, (0, 0), (w, 8), (60, 60, 60), 1)

        # Progress bar along the bottom showing position within the batch
        progress_w = int(w * (frame_idx + 1) / max(total_frames, 1))
        cv2.rectangle(img, (0, h - 5), (w, h - 1), (40, 40, 40), -1)
        cv2.rectangle(img, (0, h - 5), (progress_w, h - 1), (180, 180, 180), -1)

        def text(canvas, msg, y, color=(255, 255, 255)):
            cv2.putText(canvas, msg, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, msg, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

        state_label = "ANOMALY" if anomalous else "NORMAL"
        state_color = (0, 0, 220) if anomalous else (0, 220, 0)
        text(img, f"Score: {score:.3f}  [{state_label}]", 35, state_color)

        y = 58
        for name, s in component_scores.items():
            text(img, f"  {name}: {s:.3f}", y)
            y += 20

        text(img, f"cam: {self.camera_id}  frame {frame_idx + 1}/{total_frames}", h - 12)

        for track_id, xyxy in bboxes.items():
            if hasattr(xyxy, '__len__') and len(xyxy) >= 4:
                x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 200, 255), 2)
                cv2.putText(img, f"#{track_id}", (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1, cv2.LINE_AA)

        _, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return jpg.tobytes()

    def _write_temp_video(self, frames: list[np.ndarray]) -> Optional[str]:
        if not frames:
            return None
        h, w = frames[0].shape[:2]
        fd, tmp_path = tempfile.mkstemp(
            suffix=".mp4", prefix=f"omnisight_{self.camera_id}_"
        )
        os.close(fd)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            tmp_path, fourcc, float(self.config.TARGET_FPS), (w, h)
        )
        if not writer.isOpened():
            logger.error("[%s] Failed to open VideoWriter for temp video", self.camera_id)
            os.unlink(tmp_path)
            return None

        for f in frames:
            writer.write(f)
        writer.release()
        return tmp_path

    # ------------------------------------------------------------------
    # Incident dispatch
    # ------------------------------------------------------------------

    def _upload_clip_s3(self, frames: list[np.ndarray], event_id: str) -> Optional[str]:
        """Upload a clip to S3 and return the presigned URL, or None on failure."""
        if not self._s3 or not frames:
            return None
        mp4_bytes = _encode_to_mp4(frames, fps=5.0)
        if not mp4_bytes:
            return None
        key = f"clips/{self.camera_id}/{event_id}.mp4"
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
            logger.warning("S3 upload failed for %s: %s", self.camera_id, e)
            return None

    def _dispatch_incident(self, pipeline_result, results, frames: list[np.ndarray]):
        skelnet_result = results.get("crime_skelnet")
        weapon_result = results.get("weapon_detection")
        videomae_result = results.get("video_mae")

        # Collect track IDs from the last few frames of SkelNet output
        track_ids: list[int] = []
        if skelnet_result:
            frame_tracks = skelnet_result.metadata.get("frame_tracks", [])
            id_counts: dict[int, int] = {}
            for fd in frame_tracks:
                for t_id in fd:
                    id_counts[t_id] = id_counts.get(t_id, 0) + 1
            track_ids = sorted(id_counts, key=lambda x: id_counts[x], reverse=True)[:2]

        track_id = self.track_manager.generate_track_id(
            self.camera_id, track_ids, time.time()
        )
        if not self.track_manager.should_send(track_id):
            return

        weapon_boxes: list = []
        if weapon_result:
            # frame_boxes is a list[list[dict]] — pick the frame with the highest score
            frame_boxes = weapon_result.metadata.get("frame_boxes", [])
            if frame_boxes:
                peak_frame = int(weapon_result.scores.argmax())
                weapon_boxes = frame_boxes[peak_frame] if peak_frame < len(frame_boxes) else []

        crime_class_raw = videomae_result.metadata.get("crime_class") if videomae_result else None
        skelnet_score = (
            float(skelnet_result.scores.max())
            if skelnet_result is not None and len(skelnet_result.scores) > 0
            else 0.0
        )

        crime_type = TrackManager.map_crime_class(
            videomae_class=crime_class_raw,
            weapon_detected=bool(weapon_boxes),
            skelnet_score=skelnet_score,
        )

        component_peaks = {
            name: float(r.scores.max()) if len(r.scores) > 0 else 0.0
            for name, r in results.items()
        }
        confidence = TrackManager.calculate_confidence(
            pipeline_result.peak_score, component_peaks
        )

        ai_metadata: dict = {
            "component_scores": component_peaks,
            "fused_peak": pipeline_result.peak_score,
            "micro_batch_seconds": self.config.MICRO_BATCH_SECONDS,
        }
        if weapon_boxes:
            ai_metadata["boundingBoxes"] = weapon_boxes
        if track_ids:
            ai_metadata["keypoints"] = True

        # Upload clip to S3 before creating the incident so videoUrl is set immediately
        event_id = str(uuid.uuid4())
        clip_frames = list(frames[-60:])  # last ~4s at 15fps
        video_url = self._upload_clip_s3(clip_frames, event_id)

        sync_result = self.incident_sender.send_sync(
            camera_code=self.camera_id,
            track_id=track_id,
            crime_type=crime_type,
            confidence=confidence,
            ai_metadata=ai_metadata,
            video_url=video_url,
        )

        if sync_result:
            self.track_manager.mark_sent(track_id)
            self._total_detections_sent += 1
            self._last_sent_track_id = track_id
            self._last_dispatch_time = time.time()

            if self._vlm_client is not None and self._vlm_executor is not None:
                self._vlm_executor.submit(
                    self._vlm_client.analyze_and_update,
                    frames=clip_frames,
                    track_id=track_id,
                    camera_id=self.camera_id,
                    zone="",
                    fusion_score=pipeline_result.peak_score,
                    incident_sender=self.incident_sender,
                    existing_video_url=video_url,
                )

    # ------------------------------------------------------------------
    # Live stream preview (for /stream endpoint)
    # ------------------------------------------------------------------

    def get_stream_frame(self) -> Optional[bytes]:
        """
        Return the next annotated frame from the completed micro-batch replay queue.
        While a new batch is being processed the last rendered frame is repeated so
        the stream never stalls.
        """
        try:
            jpg = self._replay_queue.get_nowait()
            self._last_replay_frame = jpg
            return jpg
        except queue.Empty:
            # Batch is still processing — hold the last frame
            if self._last_replay_frame is not None:
                return self._last_replay_frame
            # Nothing processed yet: render the raw incoming frame as a placeholder
            with self._frame_lock:
                if self._latest_frame is None:
                    return None
                frame = self._latest_frame.copy()
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (80, 80, 80), 6)
            cv2.putText(frame, "Accumulating batch...", (10, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA)
            pending = len(self._micro_batch_frames)
            cv2.putText(
                frame,
                f"{pending}/{self._micro_batch_target} frames  cam: {self.camera_id}",
                (10, h // 2 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA,
            )
            _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return jpg.tobytes()
