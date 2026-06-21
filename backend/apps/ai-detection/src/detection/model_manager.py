from __future__ import annotations

import gc
import logging
import os
import sys
import time

import torch

from src.core.config import Settings

logger = logging.getLogger(__name__)

# Add ai/ to sys.path so we can import pipeline.detectors.*
# Dev path (native mode): resolve ai/ relative to this file.
# Docker sets PYTHONPATH=/app:/app/ai so pipeline.* is already importable there.
_AI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../ai"))


def _ensure_ai_path():
    """Add ai/ to sys.path if pipeline isn't already importable (no-op in Docker)."""
    try:
        import pipeline  # noqa: F401 — already importable via PYTHONPATH
        return
    except ModuleNotFoundError:
        pass
    if _AI_ROOT not in sys.path:
        sys.path.insert(0, _AI_ROOT)


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
    Loads and manages AI detectors.

    Batch detectors (SkelNet, VideoMAE, Weapon) run on micro-batch video clips.
    Streaming detectors (PAAN, SurveillanceAnalytics) continue to run frame-by-frame
    or via audio tap, as they don't depend on temporal video context.
    """

    # Names managed as batch detectors (run on temp video clips)
    BATCH_NAMES = ("crime_skelnet", "video_mae", "weapon_detection")
    # Names managed as streaming-only detectors (per-frame or audio thread)
    STREAMING_NAMES = ("paan", "surveillance_analytics")

    def __init__(self, config: Settings):
        self.config = config
        self._batch_loaded: set[str] = set()
        self._streaming_loaded: set[str] = set()
        self._load_times: dict[str, float] = {}
        self._disabled: set[str] = set()
        self._ready = False

    # ------------------------------------------------------------------
    # Startup: validate that each detector can be loaded
    # ------------------------------------------------------------------

    def load_all(self):
        _ensure_ai_path()
        self._disabled = set(self.config.DISABLED_MODELS)
        device = self.config.DEVICE

        # Validate batch detectors
        for name, det in self._batch_registry():
            if name in self._disabled:
                logger.info("Skipping %s (disabled)", name)
                continue
            _free_memory()
            logger.info("Loading batch detector %s ...", name)
            t0 = time.time()
            try:
                det.load(device)
                elapsed = time.time() - t0
                self._batch_loaded.add(name)
                self._load_times[name] = elapsed
                logger.info("%s loaded in %.1fs", name, elapsed)
            except Exception as e:
                logger.error("Failed to load %s: %s", name, e, exc_info=True)
            finally:
                del det
                _free_memory()

        # Validate streaming-only detectors
        for name, det in self._streaming_registry():
            if name in self._disabled:
                logger.info("Skipping %s (disabled)", name)
                continue
            _free_memory()
            logger.info("Loading streaming detector %s ...", name)
            t0 = time.time()
            try:
                det.load(device)
                elapsed = time.time() - t0
                self._streaming_loaded.add(name)
                self._load_times[name] = elapsed
                logger.info("%s loaded in %.1fs", name, elapsed)
            except Exception as e:
                logger.error("Failed to load %s: %s", name, e, exc_info=True)
            finally:
                del det
                _free_memory()

        self._ready = True
        total = len(self._batch_loaded) + len(self._streaming_loaded)
        logger.info("Model loading complete: %d detectors ready", total)

    # ------------------------------------------------------------------
    # Per-camera factory methods
    # ------------------------------------------------------------------

    def create_camera_batch_detectors(self) -> dict:
        """
        Create fresh batch-detector instances for a single camera.
        Each camera needs its own SkelNet instance because YOLO .track(persist=True)
        maintains per-sequence tracker state.
        """
        _ensure_ai_path()
        device = self.config.DEVICE
        detectors: dict = {}

        for name, det in self._batch_registry():
            if name not in self._batch_loaded or name in self._disabled:
                continue
            try:
                det.load(device)
                detectors[name] = det
                logger.info("Batch detector %s ready for camera", name)
            except Exception as e:
                logger.error("Failed to create batch detector %s for camera: %s", name, e)

        return detectors

    def create_paan_detector(self):
        """Return a fresh PAANStreamingDetector if PAAN is enabled, else None."""
        if "paan" not in self._streaming_loaded or "paan" in self._disabled:
            return None
        from src.detection.streaming_adapters.paan_streaming import PAANStreamingDetector
        det = PAANStreamingDetector()
        try:
            det.load(self.config.DEVICE)
            return det
        except Exception as e:
            logger.error("Failed to create PAAN detector: %s", e)
            return None

    def create_sa_detector(self):
        """Return a fresh SurveillanceStreamingDetector if SA is enabled, else None."""
        if "surveillance_analytics" not in self._streaming_loaded or "surveillance_analytics" in self._disabled:
            return None
        from src.detection.streaming_adapters.surveillance_streaming import SurveillanceStreamingDetector
        det = SurveillanceStreamingDetector(disabled_modules=self.config.DISABLED_SA_MODULES)
        try:
            det.load(self.config.DEVICE)
            return det
        except Exception as e:
            logger.error("Failed to create SA detector: %s", e)
            return None

    # ------------------------------------------------------------------
    # Registries
    # ------------------------------------------------------------------

    def _batch_registry(self) -> list[tuple[str, object]]:
        from pipeline.detectors import SkelNetDetector, VideoMAEDetector, WeaponDetector
        return [
            ("weapon_detection", WeaponDetector(
                weights_path=self.config.WEAPON_WEIGHTS,
                sample_fps=2,
            )),
            ("crime_skelnet", SkelNetDetector(
                weights_path=self.config.SKELNET_WEIGHTS,
                pose_model=self.config.POSE_MODEL,
            )),
            ("video_mae", VideoMAEDetector(
                weights_path=self.config.VIDEOMAE_WEIGHTS,
            )),
        ]

    def _streaming_registry(self) -> list[tuple[str, object]]:
        from src.detection.streaming_adapters.paan_streaming import PAANStreamingDetector
        from src.detection.streaming_adapters.surveillance_streaming import SurveillanceStreamingDetector
        return [
            ("paan", PAANStreamingDetector()),
            ("surveillance_analytics", SurveillanceStreamingDetector(
                disabled_modules=self.config.DISABLED_SA_MODULES,
            )),
        ]

    # ------------------------------------------------------------------
    # Runtime enable/disable
    # ------------------------------------------------------------------

    @property
    def loaded_names(self) -> set[str]:
        return self._batch_loaded | self._streaming_loaded

    def get_active_names(self) -> list[str]:
        return sorted((self._batch_loaded | self._streaming_loaded) - self._disabled)

    def disable_detector(self, name: str) -> bool:
        if name in self.loaded_names:
            self._disabled.add(name)
            logger.info("Disabled detector: %s", name)
            return True
        return False

    def enable_detector(self, name: str) -> bool:
        if name in self.loaded_names:
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
