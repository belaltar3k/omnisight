import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.incident_metric import IncidentMetric

def get_heatmap_data(db: Session, start_date: datetime, end_date: datetime, crime_type: str = None) -> dict:
    query = db.query(IncidentMetric).filter(
        IncidentMetric.timestamp >= start_date,
        IncidentMetric.timestamp <= end_date
    )
    if crime_type:
        query = query.filter(IncidentMetric.crime_type == crime_type)
        
    df = pd.read_sql(query.statement, query.session.bind)
    
    if df.empty:
        return {"zones": [], "temporal_heatmap": {"hourly": {}, "daily": {}}}

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    # 1. Geographic Heatmap (By Zone)
    zone_counts = df['zone_id'].value_counts()
    max_count = zone_counts.max() if not zone_counts.empty else 1
    zones_data = [
        {
            "zone_id": str(zone_id),
            "incident_count": int(count),
            "intensity": round(count / max_count, 2) # Normalize between 0 and 1
        }
        for zone_id, count in zone_counts.items()
    ]

    # 2. Temporal Heatmap (By Hour and Day)
    df['hour'] = df['timestamp'].dt.strftime('%H')
    df['day'] = df['timestamp'].dt.day_name().str.lower()
    
    hourly_counts = df['hour'].value_counts().to_dict()
    daily_counts = df['day'].value_counts().to_dict()

    return {
        "zones": zones_data,
        "temporal_heatmap": {
            "hourly": hourly_counts,
            "daily": daily_counts
        }
    }