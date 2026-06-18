import json
import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Tuple

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Comma-separated or JSON array of RTSP URLs.
    # Set via RTSP_URLS env var:
    #   RTSP_URLS='["rtsp://user:pass@192.168.1.10:554/stream1","rtsp://user:pass@192.168.1.11:554/stream2"]'
    # No default — service starts with zero cameras if not configured (logs a warning).
    RTSP_URLS: List[str] = []

    TARGET_FPS: int = 30
    RESOLUTION: Tuple[int, int] = (1920, 1080)
    BUFFER_SIZE: int = 300
    RECONNECT_ATTEMPTS: int = 5
    RECONNECT_DELAY: List[int] = [1, 2, 4, 8, 16]
    # Seconds to wait before re-entering the reconnect cycle after all attempts exhausted
    RECONNECT_COOLDOWN: int = 60
    HEALTH_CHECK_INTERVAL: int = 30
    CODEC: str = "h264"
    TRANSPORT: str = "tcp"

    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 640

    # IPC for AI Detection
    IPC_SHARED_MEMORY_PREFIX: str = "cam_"

    @field_validator("RTSP_URLS", mode="before")
    @classmethod
    def parse_rtsp_urls(cls, v):
        if isinstance(v, str):
            v = v.strip()
            # Accept JSON array string or comma-separated plain URLs
            if v.startswith("["):
                return json.loads(v)
            return [u.strip() for u in v.split(",") if u.strip()]
        return v

    class Config:
        env_file = ".env"


config = Settings()

if not config.RTSP_URLS:
    logger.warning(
        "RTSP_URLS is not configured — no cameras will be started. "
        "Set RTSP_URLS in the environment or .env file."
    )
