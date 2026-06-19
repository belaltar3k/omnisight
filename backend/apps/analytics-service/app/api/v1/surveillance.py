from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.surveillance_metric import SurveillanceMetric

router = APIRouter(prefix="/surveillance", tags=["Surveillance Analytics"])


# ── Ingest ──────────────────────────────────────────────────────────────────

class SurveillanceIngestPayload(BaseModel):
    camera_id: str
    persons: int = 0
    vehicles: int = 0
    total_alerts: int = 0
    modules: dict = {}


@router.post("/ingest", status_code=201)
def ingest(payload: SurveillanceIngestPayload, db: Session = Depends(get_db)):
    row = SurveillanceMetric(
        id=uuid.uuid4(),
        timestamp=datetime.now(timezone.utc),
        camera_id=payload.camera_id,
        persons=payload.persons,
        vehicles=payload.vehicles,
        total_alerts=payload.total_alerts,
        modules=payload.modules,
    )
    db.add(row)
    db.commit()
    return {"ok": True}


# ── Query helpers ────────────────────────────────────────────────────────────

def _window(hours: int = 1) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(hours=hours), now


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/latest")
def get_latest(db: Session = Depends(get_db)):
    """Most recent snapshot per camera."""
    sql = text("""
        SELECT DISTINCT ON (camera_id)
            camera_id, timestamp, persons, vehicles, total_alerts, modules
        FROM surveillance_metrics
        ORDER BY camera_id, timestamp DESC
    """)
    rows = db.execute(sql).mappings().all()
    return {
        "cameras": [
            {
                "camera_id": r["camera_id"],
                "timestamp": r["timestamp"].isoformat(),
                "persons": r["persons"],
                "vehicles": r["vehicles"],
                "total_alerts": r["total_alerts"],
                "modules": r["modules"],
            }
            for r in rows
        ]
    }


@router.get("/crowd")
def get_crowd(hours: int = 1, camera_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Crowd metrics (persons, crowd_density module) over the last N hours."""
    start, end = _window(hours)
    q = db.query(SurveillanceMetric).filter(
        SurveillanceMetric.timestamp >= start,
        SurveillanceMetric.timestamp <= end,
    )
    if camera_id:
        q = q.filter(SurveillanceMetric.camera_id == camera_id)
    rows = q.order_by(SurveillanceMetric.timestamp.asc()).all()

    series = []
    for r in rows:
        crowd = r.modules.get("crowd_density", {})
        series.append({
            "timestamp": r.timestamp.isoformat(),
            "camera_id": r.camera_id,
            "persons": r.persons,
            "current_count": crowd.get("current_count", r.persons),
            "rolling_avg": crowd.get("rolling_avg"),
            "peak_count": crowd.get("peak_count"),
            "capacity_utilization_pct": crowd.get("capacity_utilization_pct"),
            "trend_direction": crowd.get("trend_direction"),
            "zone_current": crowd.get("zone_current", {}),
        })

    return {"window_hours": hours, "points": len(series), "series": series}


@router.get("/traffic")
def get_traffic(hours: int = 1, camera_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Traffic metrics (vehicles, speed, throughput) over the last N hours."""
    start, end = _window(hours)
    q = db.query(SurveillanceMetric).filter(
        SurveillanceMetric.timestamp >= start,
        SurveillanceMetric.timestamp <= end,
    )
    if camera_id:
        q = q.filter(SurveillanceMetric.camera_id == camera_id)
    rows = q.order_by(SurveillanceMetric.timestamp.asc()).all()

    series = []
    for r in rows:
        speed = r.modules.get("speed_statistics", {})
        throughput = r.modules.get("traffic_throughput", {})
        density = r.modules.get("traffic_density", {})
        series.append({
            "timestamp": r.timestamp.isoformat(),
            "camera_id": r.camera_id,
            "vehicles": r.vehicles,
            "mean_speed": speed.get("mean_speed"),
            "median_speed": speed.get("median_speed"),
            "speeding_rate": speed.get("speeding_rate"),
            "speed_limit": speed.get("speed_limit"),
            "throughput": throughput.get("total_count"),
            "traffic_density": density.get("density_level"),
        })

    return {"window_hours": hours, "points": len(series), "series": series}


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Full summary: latest snapshot with all 19 module outputs per camera."""
    sql = text("""
        SELECT DISTINCT ON (camera_id)
            camera_id, timestamp, persons, vehicles, total_alerts, modules
        FROM surveillance_metrics
        ORDER BY camera_id, timestamp DESC
    """)
    rows = db.execute(sql).mappings().all()

    if not rows:
        return {"cameras": [], "totals": {"persons": 0, "vehicles": 0, "alerts": 0}}

    cameras = []
    total_persons = total_vehicles = total_alerts = 0
    for r in rows:
        total_persons += r["persons"]
        total_vehicles += r["vehicles"]
        total_alerts += r["total_alerts"]
        cameras.append({
            "camera_id": r["camera_id"],
            "timestamp": r["timestamp"].isoformat(),
            "persons": r["persons"],
            "vehicles": r["vehicles"],
            "total_alerts": r["total_alerts"],
            "crowd": r["modules"].get("crowd_density", {}),
            "queue": r["modules"].get("queue_analytics", {}),
            "zone_occupancy": r["modules"].get("zone_occupancy", {}),
            "flow_anomaly": r["modules"].get("flow_anomaly_index", {}),
            "gathering": r["modules"].get("gathering_statistics", {}),
            "speed": r["modules"].get("speed_statistics", {}),
            "traffic_density": r["modules"].get("traffic_density", {}),
            "throughput": r["modules"].get("traffic_throughput", {}),
            "direction_flow": r["modules"].get("directional_flow", {}),
            "parking": r["modules"].get("parking_occupancy", {}),
            "crossing": r["modules"].get("crossing_usage", {}),
            "heatmap": r["modules"].get("activity_heatmap", {}),
            "dwell_time": r["modules"].get("dwell_time", {}),
            "movement_patterns": r["modules"].get("movement_patterns", {}),
            "object_distribution": r["modules"].get("object_distribution", {}),
            "pedestrian_flow": r["modules"].get("pedestrian_flow", {}),
            "peak_analysis": r["modules"].get("peak_analysis", {}),
            "trend_monitor": r["modules"].get("trend_monitor", {}),
            "hourly_report": r["modules"].get("hourly_report", {}),
            "scene_baseline": r["modules"].get("scene_baseline", {}),
        })

    return {
        "cameras": cameras,
        "totals": {
            "persons": total_persons,
            "vehicles": total_vehicles,
            "alerts": total_alerts,
        },
    }
