from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.api.dependencies import get_db
from app.schemas.analytics import IncidentStatsResponse, TimeSeriesResponse, ResponseTimeStats
from app.services import statistics, time_series

router = APIRouter(prefix="/incidents", tags=["Incident Analytics"])

@router.get("/stats", response_model=IncidentStatsResponse)
def get_stats(
    date_from: datetime = None, 
    date_to: datetime = None, 
    db: Session = Depends(get_db)
):
    if not date_from:
        date_from = datetime.now(timezone.utc) - timedelta(days=30)
    if not date_to:
        date_to = datetime.now(timezone.utc)
        
    stats = statistics.get_incident_stats(db, date_from, date_to)
    return stats

@router.get("/trends", response_model=TimeSeriesResponse)
def get_trends(
    interval: str = 'D',
    date_from: datetime = None, 
    date_to: datetime = None, 
    db: Session = Depends(get_db)
):
    if not date_from:
        date_from = datetime.now(timezone.utc) - timedelta(days=30)
    if not date_to:
        date_to = datetime.now(timezone.utc)
        
    return time_series.get_incident_trends(db, date_from, date_to, interval)

@router.get("/response-times", response_model=ResponseTimeStats)
def get_response_times_endpoint(
    date_from: datetime = None, 
    date_to: datetime = None, 
    db: Session = Depends(get_db)
):
    if not date_from:
        date_from = datetime.now(timezone.utc) - timedelta(days=30)
    if not date_to:
        date_to = datetime.now(timezone.utc)
        
    return statistics.get_response_times(db, date_from, date_to)