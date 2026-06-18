from __future__ import annotations

import logging
import time
import threading
from collections import deque
from multiprocessing import shared_memory
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SharedMemoryFrameReader:
    """Reads frames from shared memory blocks created by video-ingestion (Docker IPC mode)."""

    def __init__(self, camera_id: str, ipc_prefix: str, width: int, height: int):
        self.camera_id = camera_id
        self.shm_name = f"{ipc_prefix}{camera_id}"
        self.frame_shape = (height, width, 3)
        self._shm: Optional[shared_memory.SharedMemory] = None

    def _attach(self) -> bool:
        if self._shm is not None:
            return True
        try:
            self._shm = shared_memory.SharedMemory(create=False, name=self.shm_name)
            logger.info("Attached to shared memory '%s'", self.shm_name)
            return True
        except FileNotFoundError:
            return False

    def read(self) -> Optional[np.ndarray]:
        if not self._attach():
            return None
        try:
            frame = np.ndarray(self.frame_shape, dtype=np.uint8, buffer=self._shm.buf).copy()
        except Exception as e:
            logger.error("Failed to read from shared memory '%s': %s", self.shm_name, e)
            self._detach()
            return None
        if frame.max() == 0:
            return None
        return frame

    def _detach(self):
        if self._shm is not None:
            try:
                self._shm.close()
            except Exception:
                pass
            self._shm = None

    def wait_ready(self, timeout: int = 60) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._attach():
                return True
            time.sleep(1)
        logger.warning("Shared memory '%s' not available after %ds", self.shm_name, timeout)
        return False

    def close(self):
        self._detach()


class RTSPFrameReader:
    """Reads frames directly from an RTSP stream (native mode, no shared memory needed)."""

    def __init__(self, camera_id: str, rtsp_url: str, width: int, height: int, target_fps: int = 15):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.width = width
        self.height = height
        self.target_fps = target_fps

        self._cap: Optional[cv2.VideoCapture] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _open_cap(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        # Keep only the latest decoded frame — avoids reading stale buffered frames
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _capture_loop(self):
        reconnect_delays = [1, 2, 4, 8, 16]
        attempt = 0

        while self._running:
            try:
                self._cap = self._open_cap()
                if not self._cap.isOpened():
                    raise ConnectionError(f"Cannot open RTSP: {self.rtsp_url}")

                logger.info("RTSP connected: %s for %s", self.rtsp_url, self.camera_id)
                attempt = 0

                while self._running and self._cap.isOpened():
                    ret, frame = self._cap.read()
                    if not ret:
                        break
                    resized = cv2.resize(frame, (self.width, self.height))
                    with self._lock:
                        self._latest_frame = resized

            except Exception as e:
                logger.error("RTSP error for %s: %s", self.camera_id, e)
            finally:
                if self._cap:
                    self._cap.release()

            if self._running:
                delay = reconnect_delays[min(attempt, len(reconnect_delays) - 1)]
                logger.info("Reconnecting %s in %ds (attempt %d)", self.camera_id, delay, attempt + 1)
                time.sleep(delay)
                attempt += 1

    def read(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
        return None

    def wait_ready(self, timeout: int = 60) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.read() is not None:
                return True
            time.sleep(1)
        logger.warning("RTSP not producing frames for %s after %ds", self.camera_id, timeout)
        return False

    def close(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        if self._cap:
            self._cap.release()
