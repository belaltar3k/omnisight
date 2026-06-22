from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import time
from typing import Optional

import numpy as np

from .base import FrameResult, StreamingDetector

logger = logging.getLogger(__name__)


class PAANStreamingDetector(StreamingDetector):
    """
    Audio anomaly detection via RTSP audio tap.
    Connects directly to the RTSP stream to extract audio chunks,
    then runs the 3-stage PAAN pipeline on each chunk.
    """

    name = "paan"
    modality = "audio"

    def __init__(self, rtsp_url: str = "", chunk_seconds: float = 5.0):
        self.rtsp_url = rtsp_url
        self.chunk_seconds = chunk_seconds
        self.device = "cpu"
        self.models = None
        self.paan_cfg = None
        self.paan_run = None

        self._score: float = 0.0
        self._score_hold_until: float = 0.0
        self._metadata: dict = {}
        self._audio_thread: Optional[threading.Thread] = None
        self._running = False

    def load(self, device: str) -> None:
        from components.paan.config import Config
        from components.paan.models import PAANModels
        from components.paan.inference.run_paan import run_inference

        self.device = device
        self.paan_cfg = Config()
        self.paan_cfg.device = device
        self.paan_run = run_inference

        logger.info("Loading PAAN models (YAMNet + Swin + FlexSED)")
        self.models = PAANModels(self.paan_cfg)

    def start_audio_capture(self, rtsp_url: str = ""):
        if rtsp_url:
            self.rtsp_url = rtsp_url
        if not self.rtsp_url:
            logger.warning("PAAN: no RTSP URL configured, audio detection disabled")
            return

        self._running = True
        self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._audio_thread.start()

    def _audio_loop(self):
        while self._running:
            try:
                self._capture_and_analyze()
            except Exception as e:
                logger.error("PAAN audio capture error: %s", e)
            time.sleep(0.5)

    def _capture_and_analyze(self):
        tmp_dir = tempfile.mkdtemp(prefix="paan_stream_")
        audio_path = os.path.join(tmp_dir, "chunk.wav")

        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-rtsp_transport", "tcp",
                    "-i", self.rtsp_url,
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    "-t", str(self.chunk_seconds),
                    audio_path,
                ],
                capture_output=True,
                timeout=int(self.chunk_seconds + 15),
            )

            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
                return

            paan_result = self.paan_run(audio_path, self.paan_cfg, self.models)

            yamnet_score = max((s for _, s in paan_result["yamnet_candidates"]), default=0.0)
            flexsed_score = max((s for _, s in paan_result["flexsed_results"]), default=0.0)
            combined = max(yamnet_score, flexsed_score)
            if paan_result["gunshot_verified"]:
                combined = max(combined, 0.9)

            if combined > 0:
                self._score = combined
                # Hold for 20s so at least 2 video micro-batches (each 10s) see it.
                self._score_hold_until = time.time() + 20.0
            elif time.time() >= self._score_hold_until:
                self._score = 0.0
            self._metadata = {
                "yamnet_candidates": paan_result["yamnet_candidates"],
                "gunshot_verified": paan_result["gunshot_verified"],
                "flexsed_results": paan_result["flexsed_results"],
            }

        except subprocess.TimeoutExpired:
            logger.warning("PAAN: ffmpeg audio capture timed out")
        except Exception as e:
            logger.error("PAAN analysis error: %s", e)
        finally:
            try:
                os.remove(audio_path)
                os.rmdir(tmp_dir)
            except OSError:
                pass

    def process_frame(
        self, frame: np.ndarray, frame_idx: int, timestamp: float
    ) -> Optional[FrameResult]:
        return FrameResult(score=self._score, metadata=self._metadata)

    def reset(self) -> None:
        self._score = 0.0
        self._score_hold_until = 0.0
        self._metadata = {}

    def stop(self):
        self._running = False
        if self._audio_thread:
            self._audio_thread.join(timeout=10)

    def get_metadata(self) -> dict:
        return self._metadata
