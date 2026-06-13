import time
import logging
from multiprocessing import shared_memory
import numpy as np
from src.core.config import config

logger = logging.getLogger(__name__)

class FramePublisher:
    """Publishes frames directly to OS shared memory for Zero-Copy IPC to AI Detection Service"""
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.shm_name = f"{config.IPC_SHARED_MEMORY_PREFIX}{self.camera_id}"
        
        # Calculate exactly how much memory is needed based on config (Height * Width * 3 channels (RGB) * 1 byte per pixel)
        self.frame_size = config.FRAME_HEIGHT * config.FRAME_WIDTH * 3 
        self.shm = None
        
        try:
            # Create shared memory block
            self.shm = shared_memory.SharedMemory(create=True, name=self.shm_name, size=self.frame_size)
            logger.info(f"Created Shared Memory '{self.shm_name}' for Camera {self.camera_id}")
        except FileExistsError:
            # Already exists, attach to it
            self.shm = shared_memory.SharedMemory(create=False, name=self.shm_name)
            logger.info(f"Attached to existing Shared Memory '{self.shm_name}'")

    def publish(self, frame: np.ndarray):
        if not self.shm:
            return
            
        try:
            # Zero-copy transfer directly into shared memory mapped buffer
            dest = np.ndarray(frame.shape, dtype=frame.dtype, buffer=self.shm.buf)
            dest[:] = frame[:]
        except Exception as e:
            logger.error(f"Failed to publish to shared memory {self.camera_id}: {e}")

    def close(self):
        if self.shm:
            self.shm.close()
            try:
                self.shm.unlink()
                logger.info(f"Cleaned up Shared Memory '{self.shm_name}'")
            except Exception:
                pass
