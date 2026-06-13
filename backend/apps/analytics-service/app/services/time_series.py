import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.incident_metric import IncidentMetric

def get_incident_trends(db: Session, start_date: datetime, end_date: datetime, interval: str = 'D') -> dict:
    """
    Groups incidents over time (Daily by default).
    interval: 'D' for daily, 'W' for weekly, 'h' for hourly
    """
    query = db.query(IncidentMetric).filter(
        IncidentMetric.timestamp >= start_date,
        IncidentMetric.timestamp <= end_date
    )
    df = pd.read_sql(query.statement, query.session.bind)
    
    if df.empty:
        return {"interval": interval, "data": []}

    # Convert timestamp to Pandas Datetime and set as index
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.set_index('timestamp', inplace=True)

    # Resample time-series data
    resampled = df.resample(interval)
    
    trends = []
    for date, group in resampled:
        if group.empty:
            continue
        
        trends.append({
            "date": date.strftime("%Y-%m-%d %H:%M:%S" if interval == 'h' else "%Y-%m-%d"),
            "count": int(len(group)),
            "crimes": group['crime_type'].value_counts().to_dict()
        })

    return {
        "interval": "daily" if interval == 'D' else "hourly",
        "data": trends
    }