import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class VLMAnalysis(Base):
    __tablename__ = "vlm_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)

    track_id = Column(String(255), index=True, nullable=False)
    camera_id = Column(String(100), index=True, nullable=False)
    zone = Column(String(255), nullable=True)

    crime_type = Column(String(50), index=True, nullable=False, default="abnormal")
    vlm_score = Column(String(20), nullable=True)   # LOW / MEDIUM / HIGH
    people_count = Column(Integer, default=0)
    caption = Column(Text, nullable=True)
    events = Column(JSONB, default=list)
    evidence = Column(JSONB, default=list)
    video_url = Column(Text, nullable=True)
    full_json = Column(JSONB, default=dict)
