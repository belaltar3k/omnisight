from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("surveillance_analytics.dashboard")

_latest_frame: bytes | None = None
_latest_alerts: list[dict] = []
_latest_stats: dict[str, Any] = {}
_data_lock = threading.Lock()


def update_dashboard_data(frame: np.ndarray, alerts: list[dict], stats: dict):
    global _latest_frame, _latest_alerts, _latest_stats
    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    with _data_lock:
        _latest_frame = jpeg.tobytes()
        _latest_alerts = alerts
        _latest_stats = stats


def _create_app():
    import os

    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="OmniSight Smart City Dashboard")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    active_connections: list[WebSocket] = []

    @app.get("/")
    async def dashboard():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return HTMLResponse("<h1>OmniSight Dashboard</h1><p>index.html not found</p>")

    @app.get("/api/alerts")
    async def get_alerts():
        with _data_lock:
            return _latest_alerts

    @app.get("/api/stats")
    async def get_stats():
        with _data_lock:
            return _latest_stats

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        active_connections.append(ws)
        logger.info("Dashboard client connected (%d total)", len(active_connections))
        try:
            while True:
                with _data_lock:
                    frame_data = _latest_frame
                    alerts_data = _latest_alerts
                    stats_data = _latest_stats

                if frame_data:
                    message = {
                        "frame": base64.b64encode(frame_data).decode("ascii"),
                        "alerts": _serialize_alerts(alerts_data),
                        "stats": _serialize_stats(stats_data),
                        "timestamp": time.time(),
                    }
                    try:
                        await ws.send_text(json.dumps(message))
                    except Exception:
                        break

                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            pass
        finally:
            if ws in active_connections:
                active_connections.remove(ws)
            logger.info("Dashboard client disconnected (%d remaining)", len(active_connections))

    return app


def _serialize_alerts(alerts: list[dict]) -> list[dict]:
    safe = []
    for a in alerts[:20]:
        safe.append({
            "id": a.get("id", ""),
            "timestamp": a.get("timestamp", ""),
            "type": a.get("type", ""),
            "severity": a.get("severity", "info"),
            "message": a.get("message", ""),
        })
    return safe


def _serialize_stats(stats: dict) -> dict:
    safe = {}
    for k, v in stats.items():
        if isinstance(v, (int, float, str, bool)):
            safe[k] = v
        elif isinstance(v, dict):
            safe[k] = {sk: sv for sk, sv in v.items() if isinstance(sv, (int, float, str, bool))}
    return safe


def start_dashboard(config):
    import uvicorn
    app = _create_app()
    uvicorn.run(app, host=config.dashboard_host, port=config.dashboard_port, log_level="warning")
