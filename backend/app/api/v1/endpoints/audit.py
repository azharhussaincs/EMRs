from typing import List
from fastapi import APIRouter, Query
from app.core.audit import AuditEvent, audit_service

router = APIRouter()


@router.get("/logs", response_model=List[AuditEvent], summary="Retrieve Recent Audit Log Events")
async def get_audit_trail(
    limit: int = Query(default=25, ge=1, le=100, description="Max audit entries to retrieve")
) -> List[AuditEvent]:
    """
    Returns immutable audit events for compliance inspections and security verification.
    """
    return audit_service.get_recent_events(limit=limit)
