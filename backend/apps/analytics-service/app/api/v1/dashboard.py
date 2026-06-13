from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.api.dependencies import get_db
from app.schemas.dashboard import DashboardResponse, DashboardSummary
from app.services.spatial import get_heatmap_data
from app.services.statistics import get_incident_stats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/", response_model=DashboardResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stats_today = get_incident_stats(db, start_of_day, now)
    heatmap_today = get_heatmap_data(db, start_of_day, now)

    # Calculate active incidents (status: new, acknowledged, investigating, dispatched, on_scene)
    active_incidents = stats_today.get("by_status", {}).get("new", 0) + stats_today.get("by_status", {}).get("acknowledged", 0)

    summary = DashboardSummary(
        total_incidents_today=stats_today.get("total_incidents", 0),
        active_incidents=active_incidents,
        false_positive_rate_today=stats_today.get("false_positive_rate", 0.0)
    )

    return DashboardResponse(
        summary=summary,
        incidents_by_hour_today=heatmap_today["temporal_heatmap"]["hourly"],
        top_zones_by_incidents=heatmap_today["zones"][:5], # Top 5 zones
        crime_type_distribution=stats_today.get("by_crime_type", {})
    )