import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class SurveillanceMetric(Base):
    __tablename__ = "surveillance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, index=True, nullable=False)

    camera_id = Column(String(100), index=True, nullable=False)
    persons = Column(Integer, default=0)
    vehicles = Column(Integer, default=0)
    total_alerts = Column(Integer, default=0)
    modules = Column(JSONB, default=dict)
