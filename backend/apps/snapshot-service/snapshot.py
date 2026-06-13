"""
snapshot.py — reads frames from video-ingestion's shared memory IPC and
saves one JPEG snapshot per camera every SNAPSHOT_INTERVAL seconds.

Shared memory layout (written by video-ingestion/src/ipc/shared_memory.py):
  name : cam_<camera_id>          (IPC_SHARED_MEMORY_PREFIX + camera_id)
  size : FRAME_HEIGHT * FRAME_WIDTH * 3  (uint8 RGB, row-major)
  shape: (FRAME_HEIGHT, FRAME_WIDTH, 3)

Environment variables:
  CAMERA_IDS          comma-separated list of camera IDs to snapshot
                      (default: "cam-001")
  FRAME_WIDTH         must match video-ingestion config (default: 640)
  FRAME_HEIGHT        must match video-ingestion config (default: 640)
  IPC_PREFIX          shared memory name prefix (default: "cam_")
  SNAPSHOT_INTERVAL   seconds between snapshots (default: 60)
  OUTPUT_DIR          directory to save JPEGs (default: ./snapshots)
"""

import os
import time
import logging
import signal
import sys
from datetime import datetime
from multiprocessing import shared_memory

import numpy as np
import cv2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("snapshot-service")


def parse_list(env_val: str, default: list[str]) -> list[str]:
    v = os.environ.get(env_val, "")
    if not v.strip():
        return default
    return [x.strip() for x in v.split(",") if x.strip()]


CAMERA_IDS = parse_list("CAMERA_IDS", ["cam-001"])
FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", 640))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", 640))
IPC_PREFIX = os.environ.get("IPC_PREFIX", "cam_")
SNAPSHOT_INTERVAL = int(os.environ.get("SNAPSHOT_INTERVAL", 60))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./snapshots")

FRAME_SIZE = FRAME_HEIGHT * FRAME_WIDTH * 3
FRAME_SHAPE = (FRAME_HEIGHT, FRAME_WIDTH, 3)

os.makedirs(OUTPUT_DIR, exist_ok=True)

running = True


def handle_signal(sig, frame):
    global running
    logger.info("Shutdown signal received, exiting...")
    running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def snapshot_camera(camera_id: str) -> bool:
    """
    Attach to the shared memory block for camera_id, copy one frame,
    save it as a JPEG. Returns True on success.
    """
    shm_name = f"{IPC_PREFIX}{camera_id}"
    try:
        shm = shared_memory.SharedMemory(create=False, name=shm_name)
    except FileNotFoundError:
        logger.debug(f"Shared memory '{shm_name}' not ready yet (video-ingestion still starting?)")
        return False

    try:
        frame = np.ndarray(FRAME_SHAPE, dtype=np.uint8, buffer=shm.buf).copy()
    finally:
        shm.close()

    if frame.max() == 0:
        logger.warning(f"{camera_id}: frame is all-black, skipping (stream may not be active yet)")
        return False

    # video-ingestion resizes with cv2 which produces BGR, but FramePublisher
    # copies the raw numpy array from VideoCapture which is BGR. Write as-is.
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"{camera_id}_{ts}.jpg")
    ok = cv2.imwrite(filename, frame)
    if ok:
        logger.info(f"Saved snapshot: {filename}")
    else:
        logger.error(f"cv2.imwrite failed for {filename}")
    return ok


def wait_for_shm(camera_id: str, timeout: int = 30) -> bool:
    """Poll until video-ingestion has created the shared memory block."""
    shm_name = f"{IPC_PREFIX}{camera_id}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            shm = shared_memory.SharedMemory(create=False, name=shm_name)
            shm.close()
            logger.info(f"Shared memory '{shm_name}' is ready")
            return True
        except FileNotFoundError:
            time.sleep(1)
    logger.warning(f"Shared memory '{shm_name}' not available after {timeout}s — will keep retrying each interval")
    return False


def main():
    logger.info(
        f"Snapshot service started — cameras={CAMERA_IDS}, "
        f"interval={SNAPSHOT_INTERVAL}s, output={OUTPUT_DIR}, "
        f"frame={FRAME_WIDTH}x{FRAME_HEIGHT}"
    )

    # Wait briefly for video-ingestion to create shm before first snapshot
    for cam_id in CAMERA_IDS:
        wait_for_shm(cam_id)

    while running:
        for cam_id in CAMERA_IDS:
            try:
                snapshot_camera(cam_id)
            except Exception as e:
                logger.error(f"Unexpected error snapshotting {cam_id}: {e}")

        # Sleep in small chunks so SIGTERM is handled promptly
        deadline = time.monotonic() + SNAPSHOT_INTERVAL
        while running and time.monotonic() < deadline:
            time.sleep(1)

    logger.info("Snapshot service stopped.")


if __name__ == "__main__":
    main()
