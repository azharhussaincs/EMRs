from datetime import datetime
from typing import Dict, List
from pydantic import BaseModel, Field
from app.core.config import ClinicalDomain


class SubsystemStatus(BaseModel):
    name: str
    status: str = Field(..., description="healthy | degraded | unavailable")
    details: str


class HealthCheckResponse(BaseModel):
    status: str = "operational"
    version: str
    environment: str
    timestamp: datetime
    active_clinical_domains: List[ClinicalDomain]
    subsystems: Dict[str, SubsystemStatus]
