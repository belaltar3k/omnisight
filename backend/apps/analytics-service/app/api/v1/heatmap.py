from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.api.dependencies import get_db
from app.schemas.heatmap import HeatmapResponse
from app.services.spatial import get_heatmap_data

router = APIRouter(prefix="/heatmap", tags=["Spatial Analytics"])

@router.get("/", response_model=HeatmapResponse)
def get_heatmap(
    crime_type: Optional[str] = None,
    date_from: datetime = None, 
    date_to: datetime = None, 
    db: Session = Depends(get_db)
):
    if not date_from:
        date_from = datetime.now(timezone.utc) - timedelta(days=30)
    if not date_to:
        date_to = datetime.now(timezone.utc)

    return get_heatmap_data(db, date_from, date_to, crime_type)