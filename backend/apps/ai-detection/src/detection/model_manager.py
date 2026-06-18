from __future__ import annotations

import gc
import logging
import time
from typing import Optional

import torch

from src.core.config import Settings
from src.detection.streaming_adapters.base import StreamingDetector
from src.detection.streaming_adapters.skelnet_streaming import SkelNetStreamingDetector
from src.detection.streaming_adapters.weapon_streaming import WeaponStreamingDetector
from src.detection.streaming_adapters.videomae_streaming import VideoMAEStreamingDetector
from src.detection.streaming_adapters.paan_streaming import PAANStreamingDetector
from src.detection.streaming_adapters.surveillance_streaming import SurveillanceStreamingDetector

logger = logging.getLogger(__name__)


def _free_memory():
    gc.collect()
    gc.collect()
    try:
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
    except (ImportError, RuntimeError):
        pass
    gc.collect()


class ModelManager:
    """
    Loads all enabled detector models at startup and creates per-camera
    detector instances. Stateful detectors (SkelNet, Surveillance) use
    YOLO .track(persist=True) which maintains per-sequence tracker state,
    so each camera needs its own instance. The heavy neural network weights
    are shared in GPU memory via Python references.
    """

    def __init__(self, config: Settings):
        self.config = config
        self._loaded_names: set[str] = set()
        self._load_times: dict[str, float] = {}
        self._ready = False
        self._disabled: set[str] = set()

    def load_all(self):
        self._disabled = set(self.config.DISABLED_MODELS)
        device = self.config.DEVICE

        for name, detector in self._build_registry():
            if name in self._disabled:
                logger.info("Skipping %s (disabled)", name)
                continue

            _free_memory()
            logger.info("Loading %s...", name)
            t0 = time.time()
            try:
                detector.load(device)
                elapsed = time.time() - t0
                self._loaded_names.add(name)
                self._load_times[name] = elapsed
                logger.info("%s loaded in %.1fs", name, elapsed)
            except Exception as e:
                logger.error("Failed to load %s: %s", name, e, exc_info=True)
            finally:
                _free_memory()

        self._ready = True
        total_enabled = len(self._build_registry()) - len(self._disabled)
        logger.info(
            "Model loading complete: %d/%d detectors ready",
            len(self._loaded_names), total_enabled,
        )

    def _build_registry(self) -> list[tuple[str, StreamingDetector]]:
        return [
            (
                "weapon_detection",
                WeaponStreamingDetector(
                    weights_path=self.config.WEAPON_WEIGHTS,
                    sample_fps=2,
                    target_fps=self.config.TARGET_FPS,
                ),
            ),
            (
                "crime_skelnet",
                SkelNetStreamingDetector(
                    weights_path=self.config.SKELNET_WEIGHTS,
                    pose_model=self.config.POSE_MODEL,
                    target_fps=self.config.TARGET_FPS,
                ),
            ),
            (
                "paan",
                PAANStreamingDetector(),
            ),
            (
                "video_mae",
                VideoMAEStreamingDetector(
                    weights_path=self.config.VIDEOMAE_WEIGHTS,
                ),
            ),
            (
                "surveillance_analytics",
                SurveillanceStreamingDetector(
                    disabled_modules=self.config.DISABLED_SA_MODULES,
                ),
            ),
        ]

    def create_camera_detectors(self, device: str | None = None) -> dict[str, StreamingDetector]:
        """
        Create a fresh set of detector instances for a single camera.
        Each camera needs its own instances because YOLO .track(persist=True)
        maintains per-sequence tracker state that cannot be shared.
        """
        device = device or self.config.DEVICE
        detectors: dict[str, StreamingDetector] = {}

        for name, detector in self._build_registry():
            if name not in self._loaded_names or name in self._disabled:
                continue
            try:
                detector.load(device)
                detectors[name] = detector
            except Exception as e:
                logger.error("Failed to create %s for camera: %s", name, e)

        return detectors

    def get_active_names(self) -> list[str]:
        return sorted(self._loaded_names - self._disabled)

    def disable_detector(self, name: str) -> bool:
        if name in self._loaded_names:
            self._disabled.add(name)
            logger.info("Disabled detector: %s", name)
            return True
        return False

    def enable_detector(self, name: str) -> bool:
        if name in self._loaded_names:
            self._disabled.discard(name)
            logger.info("Enabled detector: %s", name)
            return True
        logger.warning(
            "Cannot enable %s — model was not loaded at startup. Restart required.", name,
        )
        return False

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def load_times(self) -> dict[str, float]:
        return dict(self._load_times)
