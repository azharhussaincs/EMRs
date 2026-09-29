from typing import List, Optional
from fastapi import APIRouter, Request, Query
from app.schemas.evidence import (
    EvidenceRetrievalResponse,
    EvidenceSourceRegistryEntry,
    EvidenceDomainCategory,
)
from app.services.evidence_service import evidence_service

router = APIRouter()


@router.get(
    "/diabetes",
    response_model=EvidenceRetrievalResponse,
    summary="Retrieve Verified Clinical Evidence for Diabetes",
    description="Retrieves authoritative clinical guideline evidence references from registered consensus bodies (ADA, KDIGO). Does NOT call an LLM.",
)
async def get_diabetes_evidence(
    request: Request,
    patient_id: Optional[str] = Query(None, description="Optional patient reference for tailored domain mapping"),
    category: Optional[EvidenceDomainCategory] = Query(None, description="Specific evidence domain category"),
) -> EvidenceRetrievalResponse:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    return evidence_service.get_diabetes_evidence(
        patient_id=patient_id, category=category, actor_id=actor_id
    )


@router.get(
    "/cardiovascular",
    response_model=EvidenceRetrievalResponse,
    summary="Retrieve Verified Clinical Evidence for Cardiovascular Disease",
    description="Retrieves authoritative clinical guideline evidence references from registered consensus bodies (ACC/AHA). Does NOT call an LLM.",
)
async def get_cardiovascular_evidence(
    request: Request,
    patient_id: Optional[str] = Query(None, description="Optional patient reference for tailored domain mapping"),
    category: Optional[EvidenceDomainCategory] = Query(None, description="Specific evidence domain category"),
) -> EvidenceRetrievalResponse:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    return evidence_service.get_cardiovascular_evidence(
        patient_id=patient_id, category=category, actor_id=actor_id
    )


@router.get(
    "/sources",
    response_model=List[EvidenceSourceRegistryEntry],
    summary="List Registered Authoritative Evidence Sources",
    description="Returns registry of authoritative clinical practice guidelines with official publication metadata.",
)
async def list_evidence_sources() -> List[EvidenceSourceRegistryEntry]:
    return evidence_service.list_sources()

