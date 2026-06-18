from __future__ import annotations

import copy
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from ultralytics import YOLO

from surveillance_analytics.config import SmartCityConfig
from surveillance_analytics.core.alert import AlertSystem
from surveillance_analytics.core.tracker import SmartCityTracker, TrackInfo
from surveillance_analytics.core.visualizer import Visualizer

logger = logging.getLogger("surveillance_analytics.engine")


MODULE_REGISTRY: list[tuple[str, str]] = [
    # Traffic analytics
    ("surveillance_analytics.modules.traffic.speed_stats", "SpeedStatistics"),
    ("surveillance_analytics.modules.traffic.throughput", "TrafficThroughput"),
    ("surveillance_analytics.modules.traffic.density", "TrafficDensity"),
    ("surveillance_analytics.modules.traffic.direction_flow", "DirectionalFlow"),
    ("surveillance_analytics.modules.traffic.parking_occupancy", "ParkingOccupancy"),
    ("surveillance_analytics.modules.traffic.crossing_usage", "CrossingUsage"),
    # Crowd analytics
    ("surveillance_analytics.modules.crowd.density", "CrowdDensity"),
    ("surveillance_analytics.modules.crowd.gathering_stats", "GatheringStatistics"),
    ("surveillance_analytics.modules.crowd.queue_analytics", "QueueAnalytics"),
    ("surveillance_analytics.modules.crowd.flow_anomaly", "FlowAnomalyIndex"),
    ("surveillance_analytics.modules.crowd.zone_occupancy", "ZoneOccupancy"),
    # Spatial analytics
    ("surveillance_analytics.modules.analytics.heatmap", "ActivityHeatmap"),
    ("surveillance_analytics.modules.analytics.dwell", "DwellTime"),
    ("surveillance_analytics.modules.analytics.movement_patterns", "MovementPatterns"),
    ("surveillance_analytics.modules.analytics.object_distribution", "ObjectDistribution"),
    # Temporal analytics
    ("surveillance_analytics.modules.analytics.flow", "PedestrianFlow"),
    ("surveillance_analytics.modules.analytics.peak_analysis", "PeakAnalysis"),
    ("surveillance_analytics.modules.analytics.trend_monitor", "TrendMonitor"),
    ("surveillance_analytics.modules.analytics.hourly_report", "HourlyReport"),
    ("surveillance_analytics.modules.analytics.scene_baseline", "SceneBaseline"),
]


def _parse_detections(results) -> list[dict]:
    dets: list[dict] = []
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


class VideoEngine:
    def __init__(self, config: SmartCityConfig):
        self.config = config
        self.yolo = YOLO(config.yolo_model)
        self.tracker = SmartCityTracker(config)
        self.alert_system = AlertSystem(config)
        self.visualizer = Visualizer(config)

        self._modules: dict[str, object] = {}
        self._fast_modules: dict[str, object] = {}
        self._medium_modules: dict[str, object] = {}
        self._slow_modules: dict[str, object] = {}
        self._background_modules: dict[str, object] = {}

        self._module_results: dict[str, dict] = {}
        self._results_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

        self.running = False
        self.frame_count = 0
        self.fps = 0.0

        self._show_heatmap = False
        self._show_zones = True
        self._show_alerts = True

        self._dashboard_callback = None

        self._register_modules()

    def _register_modules(self):
        import importlib

        for mod_path, cls_name in MODULE_REGISTRY:
            try:
                module = importlib.import_module(mod_path)
                cls = getattr(module, cls_name)
                instance = cls(self.config)

                if cls_name in self.config.disabled_modules or instance.NAME in self.config.disabled_modules:
                    logger.info("Module %s disabled by config", instance.NAME)
                    continue

                if not instance.is_available():
                    logger.warning("Module %s skipped (model not found: %s)", instance.NAME, instance.REQUIRES_MODEL)
                    continue

                tier = instance.TIER
                self._modules[instance.NAME] = instance
                if tier == "fast":
                    self._fast_modules[instance.NAME] = instance
                elif tier == "medium":
                    self._medium_modules[instance.NAME] = instance
                elif tier == "slow":
                    self._slow_modules[instance.NAME] = instance
                elif tier == "background":
                    self._background_modules[instance.NAME] = instance

                logger.info("Registered module: %s (tier=%s)", instance.NAME, tier)

            except Exception as e:
                logger.warning("Failed to load module %s.%s: %s", mod_path, cls_name, e)

        total = len(self._modules)
        logger.info(
            "Loaded %d modules: %d fast, %d medium, %d slow, %d background",
            total,
            len(self._fast_modules),
            len(self._medium_modules),
            len(self._slow_modules),
            len(self._background_modules),
        )

    def _run_module_safe(self, name: str, module, frame, detections, tracks):
        try:
            result = module.process(frame, detections, tracks)
            with self._results_lock:
                self._module_results[name] = result or {}
        except Exception as e:
            logger.error("Module %s error: %s", name, e, exc_info=True)

    def _run_tier(self, modules: dict, frame, detections, tracks):
        for name, module in modules.items():
            self._run_module_safe(name, module, frame, detections, tracks)

    def _collect_alerts(self):
        for name, module in self._modules.items():
            try:
                alerts = module.get_alerts()
                for alert in alerts:
                    self.alert_system.submit(alert)
            except Exception:
                pass

    def set_dashboard_callback(self, fn):
        self._dashboard_callback = fn

    def run(self):
        source = self.config.video_source
        if source.isdigit():
            source = int(source)

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error("Cannot open video source: %s", self.config.video_source)
            return

        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.config.camera_fps = src_fps
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        writer = None
        if self.config.save_output_video:
            os.makedirs(self.config.output_dir, exist_ok=True)
            out_path = os.path.join(self.config.output_dir, "annotated_output.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                out_path,
                fourcc,
                src_fps,
                (self.config.process_width, self.config.process_height),
            )
            logger.info("Writing output to %s", out_path)

        self.running = True
        self.frame_count = 0
        fps_timer = time.time()
        fps_frame_count = 0

        logger.info(
            "Starting processing: source=%s (%dx%d @ %.1f FPS, %d frames)",
            self.config.video_source, src_w, src_h, src_fps,
            total_frames if total_frames > 0 else -1,
        )

        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_small = cv2.resize(frame, (self.config.process_width, self.config.process_height))

                results = self.yolo.track(
                    frame_small,
                    persist=True,
                    conf=self.config.yolo_conf,
                    iou=self.config.yolo_iou,
                    tracker=self.config.tracker_type,
                    verbose=False,
                )

                detections = _parse_detections(results)
                tracks = self.tracker.update(results)

                for name, module in self._fast_modules.items():
                    self._run_module_safe(name, module, frame_small, detections, tracks)

                if self.frame_count % self.config.medium_interval == 0 and self._medium_modules:
                    frame_copy = frame_small.copy()
                    tracks_copy = copy.deepcopy(tracks)
                    self._executor.submit(self._run_tier, self._medium_modules, frame_copy, detections, tracks_copy)

                if self.frame_count % self.config.slow_interval == 0 and self._slow_modules:
                    frame_copy = frame_small.copy()
                    tracks_copy = copy.deepcopy(tracks)
                    self._executor.submit(self._run_tier, self._slow_modules, frame_copy, detections, tracks_copy)

                if self.frame_count % self.config.background_interval == 0 and self._background_modules:
                    frame_copy = frame_small.copy()
                    tracks_copy = copy.deepcopy(tracks)
                    self._executor.submit(self._run_tier, self._background_modules, frame_copy, detections, tracks_copy)

                self._collect_alerts()

                with self._results_lock:
                    results_snapshot = dict(self._module_results)

                display = self.visualizer.draw(
                    frame_small,
                    results_snapshot,
                    tracks,
                    self.alert_system.get_recent(5),
                    show_heatmap=self._show_heatmap,
                    show_zones=self._show_zones,
                    show_alerts=self._show_alerts,
                    fps=self.fps,
                    frame_num=self.frame_count,
                    total_frames=total_frames,
                )

                if writer:
                    writer.write(display)

                if self._dashboard_callback:
                    try:
                        stats = dict(results_snapshot)
                        stats["fps"] = self.fps
                        stats["persons"] = len(self.tracker.get_persons())
                        stats["vehicles"] = len(self.tracker.get_vehicles())
                        stats["tracks"] = len(tracks)
                        self._dashboard_callback(display, self.alert_system.get_recent(10), stats)
                    except Exception:
                        pass

                cv2.imshow("OmniSight Smart City Analytics", display)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord("h"):
                    self._show_heatmap = not self._show_heatmap
                elif key == ord("z"):
                    self._show_zones = not self._show_zones
                elif key == ord("a"):
                    self._show_alerts = not self._show_alerts
                elif key == ord("s"):
                    screenshot_path = os.path.join(self.config.output_dir, f"screenshot_{self.frame_count:06d}.jpg")
                    cv2.imwrite(screenshot_path, display)
                    logger.info("Screenshot saved: %s", screenshot_path)

                self.frame_count += 1
                fps_frame_count += 1
                elapsed = time.time() - fps_timer
                if elapsed >= 1.0:
                    self.fps = fps_frame_count / elapsed
                    fps_frame_count = 0
                    fps_timer = time.time()

                    if self.frame_count % 30 == 0:
                        persons = len(self.tracker.get_persons())
                        vehicles = len(self.tracker.get_vehicles())
                        self.alert_system.log_analytics(persons, vehicles, 0.0)

                if total_frames > 0 and self.frame_count % 100 == 0:
                    pct = self.frame_count / total_frames * 100
                    logger.info("Progress: %d/%d (%.1f%%) @ %.1f FPS", self.frame_count, total_frames, pct, self.fps)

        finally:
            self.running = False
            if writer:
                writer.release()
            cap.release()
            cv2.destroyAllWindows()
            self._executor.shutdown(wait=True)
            logger.info("Processing complete. %d frames processed.", self.frame_count)
