from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import pandas as pd
from app.api.dependencies import get_db
from app.models.camera_metric import CameraMetric

router = APIRouter(prefix="/cameras", tags=["Camera Analytics"])

@router.get("/performance")
def get_camera_performance(
    date_from: datetime = None, 
    date_to: datetime = None, 
    db: Session = Depends(get_db)
):
    if not date_from:
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
    if not date_to:
        date_to = datetime.now(timezone.utc)

    query = db.query(CameraMetric).filter(
        CameraMetric.timestamp >= date_from,
        CameraMetric.timestamp <= date_to
    )
    df = pd.read_sql(query.statement, query.session.bind)

    if df.empty:
        return {"cameras": []}

    # Average metrics per camera using Pandas
    grouped = df.groupby('camera_code').agg({
        'uptime_percent': 'mean',
        'avg_fps': 'mean',
        'total_detections': 'sum',
        'incidents_generated': 'sum',
        'false_positive_rate': 'mean',
        'avg_detection_latency_ms': 'mean'
    }).reset_index()

    return {"cameras": grouped.to_dict(orient="records")}