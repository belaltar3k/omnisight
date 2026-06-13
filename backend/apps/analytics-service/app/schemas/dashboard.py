from pydantic import BaseModel
from typing import Dict, List
from app.schemas.heatmap import ZoneHeatmapData

class DashboardSummary(BaseModel):
    total_incidents_today: int
    active_incidents: int
    false_positive_rate_today: float

class DashboardResponse(BaseModel):
    summary: DashboardSummary
    incidents_by_hour_today: Dict[str, int]
    top_zones_by_incidents: List[ZoneHeatmapData]  # Fixed: using the proper schema that allows float intensity!
    crime_type_distribution: Dict[str, int]