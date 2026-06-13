import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
import io
from app.models.incident_metric import IncidentMetric
from app.models.camera_metric import CameraMetric

def generate_csv_report(db: Session, report_type: str, start_date: datetime, end_date: datetime) -> str:
    """Generates a CSV string using Pandas based on the requested report type."""
    if report_type == "incident_summary":
        query = db.query(IncidentMetric).filter(
            IncidentMetric.timestamp >= start_date,
            IncidentMetric.timestamp <= end_date
        )
    elif report_type == "camera_performance":
        query = db.query(CameraMetric).filter(
            CameraMetric.timestamp >= start_date,
            CameraMetric.timestamp <= end_date
        )
    else:
        raise ValueError("Invalid report type")

    df = pd.read_sql(query.statement, query.session.bind)
    
    if df.empty:
        return "No data available for this period."

    # Convert DataFrame to a CSV string
    s_buf = io.StringIO()
    df.to_csv(s_buf, index=False)
    return s_buf.getvalue()