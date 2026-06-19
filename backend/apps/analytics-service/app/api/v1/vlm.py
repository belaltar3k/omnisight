from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.vlm_analysis import VLMAnalysis

router = APIRouter(prefix="/vlm", tags=["VLM Analysis"])


# ── Ingest ───────────────────────────────────────────────────────────────────

class VLMIngestPayload(BaseModel):
    track_id: str
    camera_id: str
    zone: str = ""
    crime_type: str = "abnormal"
    vlm_score: str = "MEDIUM"
    people_count: int = 0
    caption: str = ""
    events: list = []
    evidence: list = []
    video_url: str = ""
    full_json: dict = {}


@router.post("/ingest", status_code=201)
def ingest(payload: VLMIngestPayload, db: Session = Depends(get_db)):
    row = VLMAnalysis(
        id=uuid.uuid4(),
        timestamp=datetime.now(timezone.utc),
        track_id=payload.track_id,
        camera_id=payload.camera_id,
        zone=payload.zone or None,
        crime_type=payload.crime_type,
        vlm_score=payload.vlm_score,
        people_count=payload.people_count,
        caption=payload.caption or None,
        events=payload.events,
        evidence=payload.evidence,
        video_url=payload.video_url or None,
        full_json=payload.full_json,
    )
    db.add(row)
    db.commit()

    # Compute and store embedding in background thread (non-blocking)
    import concurrent.futures, threading
    def _embed():
        from app.services.embedding_service import embed_and_store
        from app.db.session import SessionLocal
        bg_db = SessionLocal()
        try:
            embed_and_store(row, bg_db)
        finally:
            bg_db.close()
    threading.Thread(target=_embed, daemon=True).start()

    return {"ok": True, "id": str(row.id)}


# ── Query ────────────────────────────────────────────────────────────────────

@router.get("/analyses")
def get_analyses(
    camera_id: Optional[str] = None,
    zone: Optional[str] = None,
    crime_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Query VLM analysis records. Used by chatbot queries like:
    'show incidents in zone X between T1 and T2'.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = db.query(VLMAnalysis).filter(VLMAnalysis.timestamp >= since)
    if camera_id:
        q = q.filter(VLMAnalysis.camera_id == camera_id)
    if zone:
        q = q.filter(VLMAnalysis.zone == zone)
    if crime_type:
        q = q.filter(VLMAnalysis.crime_type == crime_type)

    rows = q.order_by(VLMAnalysis.timestamp.desc()).limit(limit).all()
    return {
        "window_hours": hours,
        "count": len(rows),
        "analyses": [
            {
                "id": str(r.id),
                "timestamp": r.timestamp.isoformat(),
                "track_id": r.track_id,
                "camera_id": r.camera_id,
                "zone": r.zone,
                "crime_type": r.crime_type,
                "vlm_score": r.vlm_score,
                "people_count": r.people_count,
                "caption": r.caption,
                "events": r.events,
                "evidence": r.evidence,
                "video_url": r.video_url,
            }
            for r in rows
        ],
    }


@router.get("/analyses/{analysis_id}")
def get_analysis_detail(analysis_id: str, db: Session = Depends(get_db)):
    """Full detail of a single VLM analysis including raw VLM JSON (for reports/chatbot)."""
    try:
        aid = uuid.UUID(analysis_id)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid UUID")

    row = db.query(VLMAnalysis).filter(VLMAnalysis.id == aid).first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "id": str(row.id),
        "timestamp": row.timestamp.isoformat(),
        "track_id": row.track_id,
        "camera_id": row.camera_id,
        "zone": row.zone,
        "crime_type": row.crime_type,
        "vlm_score": row.vlm_score,
        "people_count": row.people_count,
        "caption": row.caption,
        "events": row.events,
        "evidence": row.evidence,
        "video_url": row.video_url,
        "full_json": row.full_json,
    }


@router.get("/summary")
def get_vlm_summary(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """Aggregate crime type counts and top captions — useful for dashboard and chatbot."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = db.query(VLMAnalysis).filter(VLMAnalysis.timestamp >= since).all()

    counts: dict[str, int] = {}
    for r in rows:
        counts[r.crime_type] = counts.get(r.crime_type, 0) + 1

    recent = sorted(rows, key=lambda r: r.timestamp, reverse=True)[:10]
    return {
        "window_hours": hours,
        "total": len(rows),
        "by_crime_type": counts,
        "recent_captions": [
            {"timestamp": r.timestamp.isoformat(), "camera_id": r.camera_id,
             "crime_type": r.crime_type, "caption": r.caption}
            for r in recent if r.caption
        ],
    }
