import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.core.logging import logger


class AuditEventType(str, Enum):
    EMR_INGESTION = "emr_ingestion"
    EMR_ACCESS = "emr_access"
    RISK_ASSESSMENT_EXECUTION = "risk_assessment_execution"
    GENAI_INFERENCE = "genai_inference"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    SECURITY_EVENT = "security_event"
    CONFIG_CHANGE = "config_change"


class AuditEvent(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: str = Field(default="system", description="User or service calling the API")
    resource_id: Optional[str] = Field(None, description="Resource identifier (e.g. anonymized patient ID or encounter ID)")
    action: str = Field(..., description="Specific action executed")
    status: str = Field(default="success", description="Outcome: success, failed, denied")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual execution metadata (no PHI)")
    integrity_hash: Optional[str] = Field(None, description="SHA256 integrity digest")

    def compute_integrity_hash(self) -> str:
        payload = f"{self.event_id}:{self.event_type}:{self.timestamp.isoformat()}:{self.actor_id}:{self.action}:{self.status}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditService:
    """
    Centralized Clinical Audit Service adhering to HIPAA §164.312(b) Audit Controls.
    Records events immutably without recording direct Protected Health Information (PHI).
    """

    def __init__(self):
        self._in_memory_audit_trail = []

    def record_event(self, event: AuditEvent) -> AuditEvent:
        if not event.integrity_hash:
            event.integrity_hash = event.compute_integrity_hash()

        self._in_memory_audit_trail.append(event)
        logger.info(
            f"AUDIT_RECORD: {event.event_type} | action={event.action} | status={event.status} | actor={event.actor_id}",
            extra={"audit": event.model_dump(mode="json")},
        )
        return event

    def get_recent_events(self, limit: int = 50) -> list[AuditEvent]:
        return self._in_memory_audit_trail[-limit:]


audit_service = AuditService()
