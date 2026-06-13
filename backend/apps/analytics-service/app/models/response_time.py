# app/models/response_time.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class ResponseTimeMetric(Base):
    __tablename__ = "response_time_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, index=True, nullable=False)
    
    incident_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    crime_type = Column(String(50), index=True, nullable=False)
    priority = Column(String(20), index=True, nullable=False)
    
    # Measured in seconds
    time_to_acknowledge_seconds = Column(Integer, nullable=True)
    time_to_resolve_seconds = Column(Integer, nullable=True)