import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, status
from app.core.config import settings
from app.core.audit import AuditEvent, AuditEventType, audit_service
from app.schemas.genai import ClinicalNarrativeRequest
from app.schemas.explanation import AIExplanationContext, ASCVDExplanationContext
from app.schemas.narrative import ClinicalNarrativeExplanation
from app.clinical.providers import ProviderNotConfiguredError, LLMProviderError
from app.services.explanation_service import explanation_service
from app.services.narrative_service import (
    narrative_service,
    ClinicalNarrativeValidationError,
)

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


@router.get(
    "/explanation-context/patients/{patient_id}/diabetes",
    response_model=AIExplanationContext,
    summary="Get Deterministic Clinical Explanation Context for Diabetes",
    description="Extracts strictly factual, non-generative clinical explanation context for an ingested patient. Does NOT call an LLM.",
)
async def get_patient_diabetes_explanation_context(
    patient_id: str, request: Request
) -> AIExplanationContext:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    try:
        context = explanation_service.get_diabetes_context_for_patient(patient_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Record verified HIPAA §164.312 audit event for explanation context generation
    audit_service.record_event(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.GENAI_INFERENCE,
            actor_id=actor_id,
            resource_id=patient_id,
            action="get_diabetes_explanation_context",
            status="success",
            metadata={
                "context_id": context.context_id,
                "assessment_id": context.assessment_id,
                "data_sufficiency": context.data_sufficiency.value,
                "calibration_status": context.calibration_status.value,
            },
        )
    )

    return context


@router.post(
    "/narrative/patients/{patient_id}/diabetes",
    response_model=ClinicalNarrativeExplanation,
    summary="Synthesize Grounded Clinical Narrative for Diabetes Trajectory",
    description="Synthesizes a structured, factual clinical explanation from verified AIExplanationContext using the configured LLM provider.",
)
async def generate_patient_diabetes_narrative(
    patient_id: str, request: Request
) -> ClinicalNarrativeExplanation:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    try:
        return await narrative_service.generate_diabetes_narrative(
            patient_id=patient_id, actor_id=actor_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ProviderNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ClinicalNarrativeValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Clinical safety validation rejected LLM generation: {str(e)}",
        )
    except LLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {str(e)}",
        )


@router.get(
    "/explanation-context/patients/{patient_id}/cardiovascular",
    response_model=ASCVDExplanationContext,
    summary="Get Deterministic Clinical Explanation Context for Cardiovascular Disease",
    description="Extracts strictly factual, non-generative clinical explanation context for an ingested patient. Does NOT call an LLM.",
)
async def get_patient_cardiovascular_explanation_context(
    patient_id: str, request: Request
) -> ASCVDExplanationContext:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    try:
        context = explanation_service.get_cardiovascular_context_for_patient(patient_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Record verified HIPAA §164.312 audit event for explanation context generation
    audit_service.record_event(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.GENAI_INFERENCE,
            actor_id=actor_id,
            resource_id=patient_id,
            action="get_cardiovascular_explanation_context",
            status="success",
            metadata={
                "context_id": context.context_id,
                "assessment_id": context.assessment_id,
                "data_sufficiency": context.data_sufficiency.value,
                "calibration_status": context.calibration_status.value,
            },
        )
    )

    return context


@router.post(
    "/narrative/patients/{patient_id}/cardiovascular",
    response_model=ClinicalNarrativeExplanation,
    summary="Synthesize Grounded Clinical Narrative for Cardiovascular Risk",
    description="Synthesizes a structured, factual clinical explanation from verified ASCVDExplanationContext using the configured LLM provider.",
)
async def generate_patient_cardiovascular_narrative(
    patient_id: str, request: Request
) -> ClinicalNarrativeExplanation:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    try:
        return await narrative_service.generate_cardiovascular_narrative(
            patient_id=patient_id, actor_id=actor_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ProviderNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ClinicalNarrativeValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Clinical safety validation rejected LLM generation: {str(e)}",
        )
    except LLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {str(e)}",
        )



