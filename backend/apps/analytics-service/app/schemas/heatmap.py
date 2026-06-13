from pydantic import BaseModel
from typing import Dict, List

class ZoneHeatmapData(BaseModel):
    zone_id: str
    incident_count: int
    intensity: float  # Normalized 0 to 1

class TemporalHeatmap(BaseModel):
    hourly: Dict[str, int]
    daily: Dict[str, int]

class HeatmapResponse(BaseModel):
    zones: List[ZoneHeatmapData]
    temporal_heatmap: TemporalHeatmap