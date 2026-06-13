import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.incident_metric import IncidentMetric
from app.models.response_time import ResponseTimeMetric

def get_incident_stats(db: Session, start_date: datetime, end_date: datetime) -> dict:
    # Query database
    query = db.query(IncidentMetric).filter(
        IncidentMetric.timestamp >= start_date,
        IncidentMetric.timestamp <= end_date
    )
    
    # Load directly into a Pandas DataFrame
    df = pd.read_sql(query.statement, query.session.bind)
    
    if df.empty:
        return {
            "total_incidents": 0, "by_crime_type": {}, "by_priority": {},
            "by_status": {}, "avg_confidence": 0.0, "false_positive_rate": 0.0
        }

    # Perform Pandas aggregations
    stats = {
        "total_incidents": int(len(df)),
        "by_crime_type": df['crime_type'].value_counts().to_dict(),
        "by_priority": df['priority'].value_counts().to_dict(),
        "by_status": df['status'].value_counts().to_dict(),
        "avg_confidence": float(df['confidence'].mean()),
        "false_positive_rate": float(df['is_false_positive'].mean())
    }
    
    return stats

def get_response_times(db: Session, start_date: datetime, end_date: datetime) -> dict:
    query = db.query(ResponseTimeMetric).filter(
        ResponseTimeMetric.timestamp >= start_date,
        ResponseTimeMetric.timestamp <= end_date
    )
    df = pd.read_sql(query.statement, query.session.bind)
    
    if df.empty:
        return {"avg_time_to_acknowledge_seconds": 0, "avg_time_to_resolve_seconds": 0, "by_priority": {}, "by_crime_type": {}}

    # Fill NaN values to avoid JSON serialization errors
    df = df.fillna(0)

    # Group by Priority
    priority_group = df.groupby('priority')[['time_to_acknowledge_seconds', 'time_to_resolve_seconds']].mean().to_dict(orient='index')
    
    # Group by Crime Type
    crime_group = df.groupby('crime_type')[['time_to_acknowledge_seconds', 'time_to_resolve_seconds']].mean().to_dict(orient='index')

    return {
        "avg_time_to_acknowledge_seconds": float(df['time_to_acknowledge_seconds'].mean()),
        "avg_time_to_resolve_seconds": float(df['time_to_resolve_seconds'].mean()),
        "by_priority": {k: {"avg_acknowledge": v['time_to_acknowledge_seconds'], "avg_resolve": v['time_to_resolve_seconds']} for k, v in priority_group.items()},
        "by_crime_type": {k: {"avg_acknowledge": v['time_to_acknowledge_seconds'], "avg_resolve": v['time_to_resolve_seconds']} for k, v in crime_group.items()}
    }