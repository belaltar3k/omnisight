# app/models/incident_metric.py
import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class IncidentMetric(Base):
    __tablename__ = "incident_metrics"

    # TimescaleDB requirement: The time column must be part of the primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, index=True, nullable=False)
    
    incident_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    crime_type = Column(String(50), index=True, nullable=False)
    priority = Column(String(20), nullable=False)  # critical, high, medium, low
    zone_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    camera_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    confidence = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)    # new, acknowledged, resolved
    is_false_positive = Column(Boolean, default=False)