import cv2
import time
import os
import numpy as np
import threading
import logging
from collections import deque
from src.core.config import config
from src.ipc.shared_memory import FramePublisher

logger = logging.getLogger(__name__)

class CameraWorker:
    def __init__(self, camera_id: str, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.buffer = deque(maxlen=config.BUFFER_SIZE)
        self.is_running = False
        self.capture = None
        self.thread = None

        self.publisher = FramePublisher(self.camera_id)

        self.status = "offline"
        self.current_fps = 0
        self.drop_count = 0
        self.current_bitrate_kbps = 0.0

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._process_stream, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
        if self.capture:
            self.capture.release()
        self.publisher.close()

    def _process_stream(self):
        # Outer loop: retry indefinitely with a cooldown after exhausting fast attempts.
        # This prevents cameras from being permanently marked offline due to a transient
        # network outage — they will re-enter the reconnect cycle after RECONNECT_COOLDOWN.
        while self.is_running:
            attempts = 0
            while self.is_running and attempts <= config.RECONNECT_ATTEMPTS:
                try:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{config.TRANSPORT}"
                    self.capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)

                    if not self.capture.isOpened():
                        raise ConnectionError(f"Failed to open RTSP stream: {self.rtsp_url}")

                    self.status = "online"
                    attempts = 0
                    logger.info(f"Connected to camera {self.camera_id}")

                    fps_time = time.time()
                    frames_processed = 0
                    bytes_processed = 0

                    while self.is_running and self.capture.isOpened():
                        ret, frame = self.capture.read()
                        if not ret:
                            logger.warning(f"Stream corrupted or EOF for {self.camera_id}")
                            break

                        bytes_processed += frame.nbytes

                        frame_resized = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

                        # Validate frame shape matches expected shared memory size before publishing
                        expected_size = config.FRAME_HEIGHT * config.FRAME_WIDTH * 3
                        if frame_resized.nbytes == expected_size:
                            if len(self.buffer) == config.BUFFER_SIZE:
                                self.drop_count += 1
                            self.buffer.append((time.time(), frame_resized))
                            self.publisher.publish(frame_resized)
                        else:
                            logger.warning(
                                f"Frame shape mismatch for {self.camera_id}: "
                                f"got {frame_resized.nbytes}B, expected {expected_size}B — skipping IPC publish"
                            )

                        frames_processed += 1

                        if time.time() - fps_time >= 1.0:
                            self.current_fps = frames_processed
                            self.current_bitrate_kbps = (bytes_processed / 1024) * 8
                            frames_processed = 0
                            bytes_processed = 0
                            fps_time = time.time()

                        time.sleep(1 / (config.TARGET_FPS * 1.5))

                except Exception as e:
                    self.status = "offline"
                    logger.error(f"Camera {self.camera_id} error: {e}")

                finally:
                    if self.capture:
                        self.capture.release()

                if self.is_running and attempts < config.RECONNECT_ATTEMPTS:
                    delay = (
                        config.RECONNECT_DELAY[attempts]
                        if attempts < len(config.RECONNECT_DELAY)
                        else config.RECONNECT_DELAY[-1]
                    )
                    logger.info(
                        f"Reconnecting {self.camera_id} in {delay}s "
                        f"(attempt {attempts + 1}/{config.RECONNECT_ATTEMPTS})..."
                    )
                    time.sleep(delay)
                    attempts += 1

            if self.is_running:
                logger.warning(
                    f"Camera {self.camera_id}: all reconnect attempts exhausted. "
                    f"Cooling down for {config.RECONNECT_COOLDOWN}s before retrying."
                )
                self.status = "offline"
                time.sleep(config.RECONNECT_COOLDOWN)
