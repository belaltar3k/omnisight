from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ReportTypeEnum(str, Enum):
    incident_summary = "incident_summary"
    camera_performance = "camera_performance"

class ReportRequest(BaseModel):
    report_type: ReportTypeEnum  # This creates a dropdown in Swagger!
    date_from: datetime
    date_to: datetime
    format: str = "csv"

class ReportResponse(BaseModel):
    message: str
    download_url: Optional[str] = None