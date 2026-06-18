from __future__ import annotations

import json
import os
import queue
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone


class AlertSystem:
    SEVERITY_ORDER = {"info": 0, "warning": 1, "high": 2, "critical": 3}

    def __init__(self, config):
        self.config = config
        db_path = os.path.join(config.output_dir, config.sqlite_db)
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._db_path = db_path
        self._init_db()
        self._cooldowns: dict[str, float] = {}
        self._alert_queue: queue.Queue = queue.Queue()
        self._listeners: list = []
        self._recent_alerts: list[dict] = []
        self._lock = threading.Lock()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL,
                zone TEXT,
                frame_path TEXT,
                metadata_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                crowd_count INTEGER,
                vehicle_count INTEGER,
                flow_score REAL,
                zone TEXT
            )
        """)
        conn.commit()
        conn.close()

    def submit(self, alert: dict):
        key = f"{alert.get('type', '')}_{alert.get('zone', '')}"
        now = time.time()

        if key in self._cooldowns:
            if now - self._cooldowns[key] < self.config.alert_cooldown_sec:
                return

        self._cooldowns[key] = now

        alert["id"] = str(uuid.uuid4())
        alert["timestamp"] = datetime.now(timezone.utc).isoformat()

        self._log_to_db(alert)
        self._alert_queue.put(alert)

        with self._lock:
            self._recent_alerts.append(alert)
            if len(self._recent_alerts) > 200:
                self._recent_alerts = self._recent_alerts[-200:]

        for listener in self._listeners:
            try:
                listener(alert)
            except Exception:
                pass

    def _log_to_db(self, alert: dict):
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT INTO alerts (id, timestamp, level, module, message, zone, frame_path, metadata_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    alert["id"],
                    alert["timestamp"],
                    alert.get("severity", "info"),
                    alert.get("type", "unknown"),
                    alert.get("message", ""),
                    alert.get("zone", ""),
                    alert.get("frame_path", ""),
                    json.dumps(alert.get("metadata", {})),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def log_analytics(self, crowd_count: int, vehicle_count: int, flow_score: float, zone: str = ""):
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT INTO analytics (timestamp, crowd_count, vehicle_count, flow_score, zone) "
                "VALUES (?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), crowd_count, vehicle_count, flow_score, zone),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_recent(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(reversed(self._recent_alerts[-limit:]))

    def get_stats(self) -> dict:
        with self._lock:
            counts = {}
            for a in self._recent_alerts:
                sev = a.get("severity", "info")
                counts[sev] = counts.get(sev, 0) + 1
            return {
                "total_alerts": len(self._recent_alerts),
                "by_severity": counts,
            }

    def add_listener(self, fn):
        self._listeners.append(fn)

    def pop_alerts(self) -> list[dict]:
        alerts = []
        while not self._alert_queue.empty():
            try:
                alerts.append(self._alert_queue.get_nowait())
            except queue.Empty:
                break
        return alerts

    def save_alert_frame(self, frame, alert: dict):
        if not self.config.save_alert_frames:
            return ""
        import cv2
        os.makedirs(self.config.alert_frames_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_{alert.get('type', 'alert')}.jpg"
        path = os.path.join(self.config.alert_frames_dir, fname)
        cv2.imwrite(path, frame)
        return path
