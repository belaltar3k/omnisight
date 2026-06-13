from pydantic import BaseModel
from typing import List, Optional

class CameraHealth(BaseModel):
    camera_id: str
    status: str
    fps: float
    bitrate_kbps: float
    drop_count: int

class EdgeNodeStatus(BaseModel):
    cameras: List[CameraHealth]
