"""
Tool functions that Groq's LLM can call to fetch real surveillance data.
Each function returns a plain dict that is JSON-serialisable.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

INCIDENT_SERVICE_URL = os.getenv("INCIDENT_SERVICE_URL", "http://incident-service:3003")
EDGE_SYNC_SECRET = os.getenv("EDGE_SYNC_SECRET", "")


# ── 1. search_incidents ───────────────────────────────────────────────────────

def search_incidents(
    db: Session,
    zone_id: Optional[str] = None,
    camera_id: Optional[str] = None,
    crime_type: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Query incident-service for matching incidents."""
    params: dict = {"limit": min(limit, 20), "sortBy": "detectedAt", "sortOrder": "desc"}
    if zone_id:
        params["zoneId"] = zone_id
    if camera_id:
        params["cameraId"] = camera_id
    if crime_type:
        params["crimeType"] = crime_type
    if from_time:
        params["dateFrom"] = from_time
    if to_time:
        params["dateTo"] = to_time

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                f"{INCIDENT_SERVICE_URL}/internal/incidents",
                params=params,
                headers={"x-edge-secret": EDGE_SYNC_SECRET},
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("data", [])
            incidents = raw if isinstance(raw, list) else raw.get("data", [])
            result = []
            for inc in incidents:
                result.append({
                    "id": inc.get("id"),
                    "detected_at": inc.get("detectedAt", "")[:19],
                    "crime_type": inc.get("crimeType"),
                    "priority": inc.get("priority"),
                    "status": inc.get("status"),
                    "camera": inc.get("cameraCode"),
                    "confidence": inc.get("confidence"),
                })
            return {"count": len(result), "incidents": result}
    except Exception as e:
        logger.warning("search_incidents failed: %s", e)
        return {"count": 0, "incidents": [], "error": str(e)}


# ── 2. search_vlm_analyses ────────────────────────────────────────────────────

def search_vlm_analyses(
    db: Session,
    zone: Optional[str] = None,
    camera_id: Optional[str] = None,
    crime_type: Optional[str] = None,
    hours: int = 24,
    limit: int = 10,
) -> dict:
    """Query vlm_analyses table for AI-generated captions and event descriptions."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    sql = "SELECT timestamp, camera_id, zone, crime_type, vlm_score, people_count, caption, events, evidence, video_url FROM vlm_analyses WHERE timestamp >= :since"
    params: dict = {"since": since}

    if zone:
        sql += " AND zone = :zone"
        params["zone"] = zone
    if camera_id:
        sql += " AND camera_id = :camera_id"
        params["camera_id"] = camera_id
    if crime_type:
        sql += " AND crime_type = :crime_type"
        params["crime_type"] = crime_type

    sql += " ORDER BY timestamp DESC LIMIT :limit"
    params["limit"] = min(limit, 10)

    try:
        rows = db.execute(text(sql), params).mappings().all()
        result = []
        for r in rows:
            result.append({
                "timestamp": r["timestamp"].isoformat()[:19],
                "camera_id": r["camera_id"],
                "zone": r["zone"],
                "crime_type": r["crime_type"],
                "vlm_score": r["vlm_score"],
                "people_count": r["people_count"],
                "caption": (r["caption"] or "")[:200],
                "events": (r["events"] or [])[:3],
            })
        return {"count": len(result), "window_hours": hours, "analyses": result}
    except Exception as e:
        logger.warning("search_vlm_analyses failed: %s", e)
        return {"count": 0, "analyses": [], "error": str(e)}


# ── 3. semantic_search ────────────────────────────────────────────────────────

def semantic_search(
    db: Session,
    query_text: str,
    zone: Optional[str] = None,
    camera_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 5,
) -> dict:
    """Vector similarity search over VLM captions using pgvector."""
    from app.services.embedding_service import embed_text
    try:
        query_vec = embed_text(query_text)
        vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        sql = """
            SELECT timestamp, camera_id, zone, crime_type, vlm_score, people_count,
                   caption, events, video_url,
                   embedding <=> :vec AS distance
            FROM vlm_analyses
            WHERE timestamp >= :since
              AND embedding IS NOT NULL
        """
        params: dict = {"vec": vec_str, "since": since}

        if zone:
            sql += " AND zone = :zone"
            params["zone"] = zone
        if camera_id:
            sql += " AND camera_id = :camera_id"
            params["camera_id"] = camera_id

        sql += " ORDER BY distance ASC LIMIT :limit"
        params["limit"] = min(limit, 5)

        rows = db.execute(text(sql), params).mappings().all()
        result = []
        for r in rows:
            result.append({
                "timestamp": r["timestamp"].isoformat()[:19],
                "camera_id": r["camera_id"],
                "zone": r["zone"],
                "crime_type": r["crime_type"],
                "caption": (r["caption"] or "")[:200],
                "similarity_score": round(1 - float(r["distance"]), 3),
            })
        return {"count": len(result), "query": query_text, "results": result}
    except Exception as e:
        logger.warning("semantic_search failed: %s", e)
        return {"count": 0, "results": [], "error": str(e)}


# ── 4. get_statistics ─────────────────────────────────────────────────────────

def get_statistics(
    db: Session,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Aggregate incident counts by crime type, priority, status."""
    if not date_from:
        date_from = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    if not date_to:
        date_to = datetime.now(timezone.utc).isoformat()

    try:
        sql = text("""
            SELECT
                crime_type,
                priority,
                status,
                COUNT(*) AS count,
                AVG(confidence) AS avg_confidence
            FROM incident_metrics
            WHERE timestamp >= :from_ts AND timestamp <= :to_ts
            GROUP BY crime_type, priority, status
            ORDER BY count DESC
        """)
        rows = db.execute(sql, {"from_ts": date_from, "to_ts": date_to}).mappings().all()

        by_crime: dict = {}
        by_priority: dict = {}
        by_status: dict = {}
        total = 0
        for r in rows:
            ct = r["crime_type"]
            pr = r["priority"]
            st = r["status"]
            cnt = int(r["count"])
            total += cnt
            by_crime[ct] = by_crime.get(ct, 0) + cnt
            by_priority[pr] = by_priority.get(pr, 0) + cnt
            by_status[st] = by_status.get(st, 0) + cnt

        return {
            "period": {"from": date_from[:19], "to": date_to[:19]},
            "total_incidents": total,
            "by_crime_type": by_crime,
            "by_priority": by_priority,
            "by_status": by_status,
        }
    except Exception as e:
        logger.warning("get_statistics failed: %s", e)
        return {"total_incidents": 0, "error": str(e)}


# ── 5. get_live_status ────────────────────────────────────────────────────────

def get_live_status(db: Session) -> dict:
    """Return the latest surveillance snapshot per camera (crowd, alerts)."""
    try:
        sql = text("""
            SELECT DISTINCT ON (camera_id)
                camera_id, timestamp, persons, vehicles, total_alerts, modules
            FROM surveillance_metrics
            ORDER BY camera_id, timestamp DESC
        """)
        rows = db.execute(sql).mappings().all()
        cameras = []
        for r in rows:
            crowd = r["modules"].get("crowd_density", {}) if r["modules"] else {}
            cameras.append({
                "camera_id": r["camera_id"],
                "last_seen": r["timestamp"].isoformat()[:19],
                "persons": r["persons"],
                "vehicles": r["vehicles"],
                "active_alerts": r["total_alerts"],
                "crowd_trend": crowd.get("trend_direction"),
                "capacity_pct": crowd.get("capacity_utilization_pct"),
            })
        return {"cameras": cameras, "total_cameras": len(cameras)}
    except Exception as e:
        logger.warning("get_live_status failed: %s", e)
        return {"cameras": [], "error": str(e)}


# ── Tool dispatch registry ────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_incidents",
            "description": "Query security incidents by zone, camera, crime type, and time range. Use this for questions about specific incidents, their status, or priority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_id": {"type": "string", "description": "Zone ID or name to filter by"},
                    "camera_id": {"type": "string", "description": "Camera code (e.g. cam-001)"},
                    "crime_type": {"type": "string", "enum": ["abnormal", "assault", "theft", "shoplifting", "vandalism", "fire", "weapon", "intrusion", "accident", "suspicious"]},
                    "from_time": {"type": "string", "description": "ISO8601 start time"},
                    "to_time": {"type": "string", "description": "ISO8601 end time"},
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "string"}], "default": 10, "description": "Max results to return"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_vlm_analyses",
            "description": "Get AI-generated descriptions of what happened in each anomaly clip. Returns captions, events observed, evidence, people count. Best for 'what happened' questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone": {"type": "string", "description": "Zone name to filter"},
                    "camera_id": {"type": "string", "description": "Camera code"},
                    "crime_type": {"type": "string"},
                    "hours": {"anyOf": [{"type": "integer"}, {"type": "string"}], "default": 24, "description": "Look back N hours"},
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "string"}], "default": 10},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "Find incidents matching a natural language description using vector similarity. Use for questions like 'find incidents where someone was chased' or 'show me fights near an entrance'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {"type": "string", "description": "Natural language description to search for"},
                    "zone": {"type": "string"},
                    "camera_id": {"type": "string"},
                    "hours": {"anyOf": [{"type": "integer"}, {"type": "string"}], "default": 24},
                    "limit": {"anyOf": [{"type": "integer"}, {"type": "string"}], "default": 5},
                },
                "required": ["query_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_statistics",
            "description": "Get aggregate counts of incidents grouped by crime type, priority, and status for a time period. Use for 'how many', 'summary', 'total' questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "ISO8601 start (defaults to 24h ago)"},
                    "date_to": {"type": "string", "description": "ISO8601 end (defaults to now)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_status",
            "description": "Get the current live state of all cameras: how many people are present, active alerts, crowd trend. Use for 'what is happening now' or 'current status' questions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


_INT_PARAMS = {"limit", "hours"}


def _coerce_args(args: dict) -> dict:
    """LLMs sometimes emit integer params as JSON strings; coerce them back."""
    if not args:
        return {}
    coerced = {}
    for k, v in args.items():
        if k in _INT_PARAMS and isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                pass
        coerced[k] = v
    return coerced


def dispatch_tool(name: str, args: dict, db: Session) -> dict:
    """Execute a tool by name with the given args and return the result dict."""
    args = _coerce_args(args)
    if name == "search_incidents":
        return search_incidents(db, **args)
    elif name == "search_vlm_analyses":
        return search_vlm_analyses(db, **args)
    elif name == "semantic_search":
        return semantic_search(db, **args)
    elif name == "get_statistics":
        return get_statistics(db, **args)
    elif name == "get_live_status":
        return get_live_status(db)
    else:
        return {"error": f"Unknown tool: {name}"}
