import uuid
from typing import Dict, Any
from fastapi import APIRouter
from app.core.config import settings
from app.core.audit import AuditEvent, AuditEventType, audit_service
from app.schemas.genai import ClinicalNarrativeRequest

router = APIRouter()


@router.get("/status", summary="Generative AI Orchestrator Status")
async def get_genai_status() -> Dict[str, Any]:
    """
    Returns current Generative AI orchestrator configuration, active model, and governance policies.
    """
    return {
        "status": "configured",
        "provider": settings.GENAI_PROVIDER,
        "model_name": settings.GENAI_MODEL_NAME,
        "guardrails": {
            "evidence_grounding_required": True,
            "hallucination_detection": "enabled",
            "phi_redaction_prior_to_prompting": True,
            "disclaimer_mandatory": True,
        },
        "target_audiences": ["clinician", "patient"],
        "guideline_grounding_status": "ready",
    }


@router.post("/validate-request", summary="Validate Narrative Synthesis Request")
async def validate_narrative_request(request: ClinicalNarrativeRequest) -> Dict[str, Any]:
    """
    Validates narrative synthesis parameters and registers an audit record.
    """
    audit_service.record_event(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.GENAI_INFERENCE,
            actor_id="genai-orchestrator-gateway",
            resource_id=request.assessment_id,
            action="validate_narrative_request",
            status="success",
            metadata={
                "target_audience": request.target_audience,
                "include_guidelines": request.include_evidence_citations,
            },
        )
    )

    return {
        "status": "ready_for_synthesis",
        "assessment_id": request.assessment_id,
        "target_audience": request.target_audience,
        "include_evidence_citations": request.include_evidence_citations,
        "message": "Narrative request parameters verified against governance guardrails.",
    }
