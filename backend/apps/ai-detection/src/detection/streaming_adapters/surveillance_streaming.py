from __future__ import annotations

import copy
import importlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np

from .base import FrameResult, StreamingDetector

logger = logging.getLogger(__name__)

MODULE_REGISTRY: list[tuple[str, str]] = [
    ("surveillance_analytics.modules.traffic.speed_stats", "SpeedStatistics"),
    ("surveillance_analytics.modules.traffic.throughput", "TrafficThroughput"),
    ("surveillance_analytics.modules.traffic.density", "TrafficDensity"),
    ("surveillance_analytics.modules.traffic.direction_flow", "DirectionalFlow"),
    ("surveillance_analytics.modules.traffic.parking_occupancy", "ParkingOccupancy"),
    ("surveillance_analytics.modules.traffic.crossing_usage", "CrossingUsage"),
    ("surveillance_analytics.modules.crowd.density", "CrowdDensity"),
    ("surveillance_analytics.modules.crowd.gathering_stats", "GatheringStatistics"),
    ("surveillance_analytics.modules.crowd.queue_analytics", "QueueAnalytics"),
    ("surveillance_analytics.modules.crowd.flow_anomaly", "FlowAnomalyIndex"),
    ("surveillance_analytics.modules.crowd.zone_occupancy", "ZoneOccupancy"),
    ("surveillance_analytics.modules.analytics.heatmap", "ActivityHeatmap"),
    ("surveillance_analytics.modules.analytics.dwell", "DwellTime"),
    ("surveillance_analytics.modules.analytics.movement_patterns", "MovementPatterns"),
    ("surveillance_analytics.modules.analytics.object_distribution", "ObjectDistribution"),
    ("surveillance_analytics.modules.analytics.flow", "PedestrianFlow"),
    ("surveillance_analytics.modules.analytics.peak_analysis", "PeakAnalysis"),
    ("surveillance_analytics.modules.analytics.trend_monitor", "TrendMonitor"),
    ("surveillance_analytics.modules.analytics.hourly_report", "HourlyReport"),
    ("surveillance_analytics.modules.analytics.scene_baseline", "SceneBaseline"),
]


def _parse_detections(results) -> list[dict]:
    dets = []
    if not results or results[0].boxes is None:
        return dets
    boxes = results[0].boxes
    for i in range(len(boxes)):
        x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().astype(int)
        conf = float(boxes.conf[i].item())
        cls = int(boxes.cls[i].item())
        tid = int(boxes.id[i].item()) if boxes.id is not None else -1
        dets.append({
            "bbox": (int(x1), int(y1), int(x2), int(y2)),
            "confidence": conf,
            "class_id": cls,
            "track_id": tid,
        })
    return dets


class SurveillanceStreamingDetector(StreamingDetector):
    """
    Runs 19 surveillance analytics modules on each frame (tier-based cadence).
    Always returns score=0.0 — this detector produces analytics data only.
    """

    name = "surveillance_analytics"
    modality = "video"

    def __init__(self, disabled_modules: list[str] | None = None):
        self.disabled_modules = disabled_modules or []
        self.device = "cpu"

        self._yolo = None
        self._tracker = None
        self._alert_system = None
        self._modules: dict[str, object] = {}
        self._fast_modules: dict[str, object] = {}
        self._medium_modules: dict[str, object] = {}
        self._slow_modules: dict[str, object] = {}
        self._module_results: dict[str, dict] = {}
        self._results_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._frame_count = 0

        self._medium_interval = 8
        self._slow_interval = 30

    def load(self, device: str) -> None:
        from ultralytics import YOLO
        from surveillance_analytics.config import SmartCityConfig
        from surveillance_analytics.core.tracker import SmartCityTracker
        from surveillance_analytics.core.alert import AlertSystem

        self.device = device
        sa_config = SmartCityConfig(device=device)

        logger.info("Loading surveillance analytics YOLO model")
        self._yolo = YOLO(sa_config.yolo_model)
        self._tracker = SmartCityTracker(sa_config)
        self._alert_system = AlertSystem(sa_config)

        for mod_path, cls_name in MODULE_REGISTRY:
            try:
                module = importlib.import_module(mod_path)
                cls = getattr(module, cls_name)
                instance = cls(sa_config)

                if instance.NAME in self.disabled_modules or cls_name in self.disabled_modules:
                    continue
                if not instance.is_available():
                    continue

                tier = instance.TIER
                self._modules[instance.NAME] = instance
                if tier == "fast":
                    self._fast_modules[instance.NAME] = instance
                elif tier == "medium":
                    self._medium_modules[instance.NAME] = instance
                elif tier == "slow":
                    self._slow_modules[instance.NAME] = instance

                logger.info("SA module registered: %s (tier=%s)", instance.NAME, tier)
            except Exception as e:
                logger.warning("Failed to load SA module %s: %s", cls_name, e)

        logger.info("Loaded %d surveillance analytics modules", len(self._modules))

    def process_frame(
        self, frame: np.ndarray, frame_idx: int, timestamp: float
    ) -> Optional[FrameResult]:
        if self._yolo is None:
            return None

        results = self._yolo.track(
            frame, persist=True, conf=0.35, iou=0.45,
            tracker="bytetrack.yaml", verbose=False,
        )
        detections = _parse_detections(results)
        tracks = self._tracker.update(results)

        for name, module in self._fast_modules.items():
            self._run_module_safe(name, module, frame, detections, tracks)

        if self._frame_count % self._medium_interval == 0 and self._medium_modules:
            frame_copy = frame.copy()
            tracks_copy = copy.deepcopy(tracks)
            self._executor.submit(
                self._run_tier, self._medium_modules, frame_copy, detections, tracks_copy
            )

        if self._frame_count % self._slow_interval == 0 and self._slow_modules:
            frame_copy = frame.copy()
            tracks_copy = copy.deepcopy(tracks)
            self._executor.submit(
                self._run_tier, self._slow_modules, frame_copy, detections, tracks_copy
            )

        self._collect_alerts()
        self._frame_count += 1

        with self._results_lock:
            stats = dict(self._module_results)

        stats["persons"] = len(self._tracker.get_persons())
        stats["vehicles"] = len(self._tracker.get_vehicles())
        stats["total_alerts"] = len(self._alert_system.get_recent(1000))

        return FrameResult(score=0.0, metadata={"stats": stats})

    def _run_module_safe(self, name, module, frame, detections, tracks):
        try:
            result = module.process(frame, detections, tracks)
            with self._results_lock:
                self._module_results[name] = result or {}
        except Exception as e:
            logger.error("SA module %s error: %s", name, e)

    def _run_tier(self, modules, frame, detections, tracks):
        for name, module in modules.items():
            self._run_module_safe(name, module, frame, detections, tracks)

    def _collect_alerts(self):
        for name, module in self._modules.items():
            try:
                alerts = module.get_alerts()
                for alert in alerts:
                    self._alert_system.submit(alert)
            except Exception:
                pass

    def reset(self) -> None:
        self._frame_count = 0
        with self._results_lock:
            self._module_results.clear()

    def get_metadata(self) -> dict:
        with self._results_lock:
            return dict(self._module_results)
