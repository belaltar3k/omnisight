from pydantic import BaseModel
from typing import Dict, List, Optional

class IncidentStatsResponse(BaseModel):
    total_incidents: int
    by_crime_type: Dict[str, int]
    by_priority: Dict[str, int]
    by_status: Dict[str, int]
    avg_confidence: float
    false_positive_rate: float

class TrendDataPoint(BaseModel):
    date: str
    count: int
    crimes: Dict[str, int]

class TimeSeriesResponse(BaseModel):
    interval: str
    data: List[TrendDataPoint]

class ResponseTimeStats(BaseModel):
    avg_time_to_acknowledge_seconds: float
    avg_time_to_resolve_seconds: float
    by_priority: Dict[str, Dict[str, float]]
    by_crime_type: Dict[str, Dict[str, float]]