import json
import logging
import os
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    SERVICE_PORT: int = 8010

    # --- Mode: "native" reads RTSP directly (for running on host with GPU),
    #           "docker" reads from shared memory IPC (for running inside Docker)
    MODE: str = "native"

    # --- Device ---
    DEVICE: str = "cuda"

    # --- Shared memory (docker mode only, must match video-ingestion) ---
    IPC_PREFIX: str = "cam_"
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 640

    # --- Model weights ---
    WEIGHTS_DIR: str = ""
    SKELNET_WEIGHTS: str = ""
    VIDEOMAE_WEIGHTS: str = ""
    WEAPON_WEIGHTS: str = ""
    POSE_MODEL: str = ""

    # --- Model selection (all enabled by default) ---
    DISABLED_MODELS: List[str] = []
    DISABLED_SA_MODULES: List[str] = []

    # --- Component weights ---
    WEIGHT_SKELNET: float = 0.45
    WEIGHT_PAAN: float = 0.25
    WEIGHT_WEAPON: float = 0.25
    WEIGHT_VIDEOMAE: float = 0.05
    WEIGHT_SURVEILLANCE: float = 0.0

    # --- Processing ---
    TARGET_FPS: int = 15
    FUSION_INTERVAL: int = 15
    ANOMALY_THRESHOLD: float = 0.55
    DOMINANCE_WEIGHT: float = 0.85
    SMOOTHING_WINDOW: int = 5
    MIN_ANOMALY_DURATION: float = 2.0
    ANOMALY_COOLDOWN: float = 3.0
    # Maximum time to stay in ANOMALOUS state before forcing COOLDOWN,
    # even if the score never drops. Prevents perpetual-anomaly on looping content.
    MAX_ANOMALY_DURATION: float = 30.0

    # --- Integration (use localhost when running natively) ---
    INCIDENT_SERVICE_URL: str = "http://localhost:3003"
    ANALYTICS_SERVICE_URL: str = "http://localhost:3006"
    EDGE_SYNC_SECRET: str = ""
    EDGE_NODE_CODE: str = "edge-node-01"

    # --- VLM ---
    VLM_URL: str = ""                # e.g. http://ec2-13-60-2-232.eu-north-1.compute.amazonaws.com
    VLM_FRAMES_SAMPLE: int = 16      # how many frames to sample from the anomaly clip
    VLM_TIMEOUT: float = 120.0       # Qwen can be slow on first call

    # --- S3 clip storage ---
    S3_ENABLED: bool = False
    S3_BUCKET: str = "omnisight-clips"
    S3_REGION: str = "eu-north-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # --- Redis (camera discovery from video-ingestion) ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6380
    CAMERA_DISCOVERY_INTERVAL: int = 10

    # --- RTSP URLs (required in native mode) ---
    RTSP_URLS: List[str] = []

    @field_validator("DISABLED_MODELS", "DISABLED_SA_MODULES", "RTSP_URLS", mode="before")
    @classmethod
    def parse_list(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                return json.loads(v)
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    class Config:
        env_file = ".env"

    def resolve_weights(self):
        if not self.WEIGHTS_DIR:
            ai_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../ai"))
            self.WEIGHTS_DIR = os.path.join(ai_root, "weights")

        if not self.SKELNET_WEIGHTS:
            self.SKELNET_WEIGHTS = os.path.join(self.WEIGHTS_DIR, "crime_skelnet", "best_anomaly_skel.pth")
        if not self.VIDEOMAE_WEIGHTS:
            self.VIDEOMAE_WEIGHTS = os.path.join(self.WEIGHTS_DIR, "video_mae", "best_model_higher_94.pth")
        if not self.WEAPON_WEIGHTS:
            self.WEAPON_WEIGHTS = os.path.join(self.WEIGHTS_DIR, "weapon_detection", "best.pt")
        if not self.POSE_MODEL:
            candidate = os.path.join(self.WEIGHTS_DIR, "yolo26l-pose.pt")
            if os.path.exists(candidate):
                self.POSE_MODEL = candidate
            else:
                # Let Ultralytics auto-download on first use
                self.POSE_MODEL = "yolo26l-pose.pt"

    def get_weights_dict(self) -> dict[str, float]:
        return {
            "crime_skelnet": self.WEIGHT_SKELNET,
            "paan": self.WEIGHT_PAAN,
            "weapon_detection": self.WEIGHT_WEAPON,
            "video_mae": self.WEIGHT_VIDEOMAE,
            "surveillance_analytics": self.WEIGHT_SURVEILLANCE,
        }


config = Settings()
config.resolve_weights()
