# app/models/camera_metric.py
import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class CameraMetric(Base):
    __tablename__ = "camera_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, index=True, nullable=False)
    
    camera_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    camera_code = Column(String(100), nullable=False)
    
    # Performance Stats
    uptime_percent = Column(Float, nullable=False)
    avg_fps = Column(Float, nullable=False)
    total_detections = Column(Integer, default=0)
    incidents_generated = Column(Integer, default=0)
    false_positive_rate = Column(Float, default=0.0)
    avg_detection_latency_ms = Column(Float, default=0.0)