from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SmartCityConfig:
    video_source: str = "0"
    process_width: int = 640
    process_height: int = 480

    # YOLO primary model
    yolo_model: str = "yolov8n.pt"
    yolo_conf: float = 0.35
    yolo_iou: float = 0.45

    # Tier intervals (in frames)
    medium_interval: int = 8
    slow_interval: int = 30
    background_interval: int = 3600

    # Module control
    disabled_modules: list[str] = field(default_factory=list)

    # Tracking
    tracker_type: str = "bytetrack.yaml"
    track_buffer: int = 60

    # Zone definitions — polygon points in (x, y) pixel coords at process resolution
    zones: dict[str, list[tuple[int, int]]] = field(default_factory=lambda: {
        "road":       [(0, 300), (640, 300), (640, 480), (0, 480)],
        "sidewalk":   [(0, 200), (640, 200), (640, 300), (0, 300)],
        "crosswalk":  [(200, 280), (440, 280), (440, 400), (200, 400)],
        "no_parking": [(0, 350), (200, 350), (200, 480), (0, 480)],
        "restricted": [(300, 0), (640, 0), (640, 200), (300, 200)],
        "checkout":   [(400, 300), (640, 300), (640, 480), (400, 480)],
        "entrance":   [(280, 230), (360, 230), (360, 270), (280, 270)],
    })

    # Thresholds
    speed_limit_kmh: float = 50.0
    crowd_max_capacity: int = 20
    queue_max_length: int = 10
    parking_timeout_sec: float = 30.0
    abandon_timeout_sec: float = 300.0
    loiter_timeout_sec: float = 120.0
    dwell_alert_sec: float = 180.0
    panic_flow_thresh: float = 0.7

    # Camera calibration
    pixels_per_meter: float = 8.0
    camera_fps: float = 30.0

    # Alert settings
    alert_cooldown_sec: float = 5.0
    save_alert_frames: bool = True
    alert_frames_dir: str = "alerts"
    sqlite_db: str = "surveillance_analytics_alerts.db"

    # Output
    output_dir: str = "output"
    save_output_video: bool = True

    # Dashboard
    dashboard_port: int = 8765
    dashboard_host: str = "0.0.0.0"

    # Device
    device: str = "cuda"

    # Counting lines for pedestrian flow: list of {name, p1, p2, direction}
    counting_lines: list[dict] = field(default_factory=lambda: [
        {"name": "entrance", "p1": (320, 200), "p2": (320, 400), "direction": "horizontal"},
    ])
