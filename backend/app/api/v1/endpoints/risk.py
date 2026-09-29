import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import ClinicalDomain
from app.core.audit import AuditEvent, AuditEventType, audit_service
from app.schemas.features import ClinicalDomainFeatures
from app.schemas.risk import (
    RiskAssessmentRequest,
    RiskAssessmentResult,
)
from app.schemas.explanation import AIExplanationContext, ASCVDExplanationContext
from app.services.risk_engine import risk_assessment_engine
from app.services.explanation_service import explanation_service

router = APIRouter()


@router.get("/capabilities", summary="List Registered Predictive Model Capabilities")
async def list_model_capabilities() -> Dict[str, Any]:
    """
    Returns metadata regarding the risk prediction pipelines designed for each clinical domain.
    """
    return {
        "engine_architecture": "Modular Multi-Disease Clinical Risk Stratification Engine",
        "supported_domains": [d.value for d in risk_assessment_engine.supported_domains()],
        "active_pathways": {
            "diabetes": "HbA1c longitudinal trajectory stratification (Active - v0.1.0)",
            "cardiovascular": "ASCVD clinical risk factor stratification (Active - v0.1.0)",
            "chronic_kidney_disease": "Planned - eGFR progression trajectory",
            "cancer": "Planned - Screening biomarker protocols",
        },
        "model_status": "foundation_pathway_operational",
        "notes": "Non-calibrated research estimator. Does not emit unvalidated clinical probabilities.",
    }


@router.get(
    "/patients/{patient_id}/diabetes",
    response_model=RiskAssessmentResult,
    summary="Assess Diabetes Trajectory Risk for Ingested Patient",
    description="Evaluates longitudinal HbA1c trajectory for an ingested patient in repository.",
)
async def assess_patient_diabetes_risk(
    patient_id: str, request: Request
) -> RiskAssessmentResult:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    try:
        result = risk_assessment_engine.assess_patient_risk(
            patient_id=patient_id, domain=ClinicalDomain.DIABETES
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Record verified HIPAA §164.312 audit event for risk assessment execution
    audit_service.record_event(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.RISK_ASSESSMENT_EXECUTION,
            actor_id=actor_id,
            resource_id=patient_id,
            action="assess_diabetes_risk",
            status="success",
            metadata={
                "assessment_id": result.assessment_id,
                "estimator_id": result.estimator_id,
                "data_sufficiency": result.data_sufficiency.value,
                "calibration_status": result.calibration_status.value,
            },
        )
    )

    return result


@router.get(
    "/patients/{patient_id}/diabetes/explanation-context",
    response_model=AIExplanationContext,
    summary="Get Factual AI Explanation Context for Diabetes",
    description="Returns deterministic, factual clinical explanation context for an ingested patient. Does NOT call an LLM.",
)
async def get_patient_diabetes_risk_explanation_context(
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
    "/evaluate/diabetes",
    response_model=RiskAssessmentResult,
    summary="Evaluate Diabetes Risk Directly From Clinical Features",
    description="Evaluates diabetes trajectory directly from pre-extracted ClinicalDomainFeatures without repository lookup.",
)
async def evaluate_features_diabetes_risk(
    features: ClinicalDomainFeatures,
) -> RiskAssessmentResult:
    return risk_assessment_engine.assess_features(
        features=features, domain=ClinicalDomain.DIABETES
    )


@router.get(
    "/models/diabetes",
    summary="Get Diabetes Estimator Model Card & Assumptions",
)
async def get_diabetes_model_card() -> Dict[str, Any]:
    return risk_assessment_engine.get_model_card(ClinicalDomain.DIABETES)


@router.get(
    "/patients/{patient_id}/cardiovascular",
    response_model=RiskAssessmentResult,
    summary="Assess Cardiovascular (ASCVD) Risk for Ingested Patient",
    description="Evaluates ASCVD clinical risk factor profile and trajectory features for an ingested patient in repository.",
)
async def assess_patient_cardiovascular_risk(
    patient_id: str, request: Request
) -> RiskAssessmentResult:
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    try:
        result = risk_assessment_engine.assess_patient_risk(
            patient_id=patient_id, domain=ClinicalDomain.CARDIOVASCULAR
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Record verified HIPAA §164.312 audit event for CVD risk assessment execution
    audit_service.record_event(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.RISK_ASSESSMENT_EXECUTION,
            actor_id=actor_id,
            resource_id=patient_id,
            action="assess_cardiovascular_risk",
            status="success",
            metadata={
                "assessment_id": result.assessment_id,
                "estimator_id": result.estimator_id,
                "data_sufficiency": result.data_sufficiency.value,
                "calibration_status": result.calibration_status.value,
            },
        )
    )

    return result


@router.get(
    "/patients/{patient_id}/cardiovascular/explanation-context",
    response_model=ASCVDExplanationContext,
    summary="Get Factual AI Explanation Context for Cardiovascular Disease",
    description="Returns deterministic, factual clinical explanation context for an ingested patient. Does NOT call an LLM.",
)
async def get_patient_cardiovascular_risk_explanation_context(
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
    "/evaluate/cardiovascular",
    response_model=RiskAssessmentResult,
    summary="Evaluate Cardiovascular Risk Directly From Clinical Features",
    description="Evaluates ASCVD risk factors directly from pre-extracted ClinicalDomainFeatures without repository lookup.",
)
async def evaluate_features_cardiovascular_risk(
    features: ClinicalDomainFeatures,
) -> RiskAssessmentResult:
    return risk_assessment_engine.assess_features(
        features=features, domain=ClinicalDomain.CARDIOVASCULAR
    )


@router.get(
    "/models/cardiovascular",
    summary="Get Cardiovascular Estimator Model Card & Assumptions",
)
async def get_cardiovascular_model_card() -> Dict[str, Any]:
    return risk_assessment_engine.get_model_card(ClinicalDomain.CARDIOVASCULAR)


@router.post("/validate-request", summary="Validate Risk Assessment Request")
async def validate_risk_assessment_request(request: RiskAssessmentRequest) -> Dict[str, Any]:
    """
    Validates clinical parameters, horizon, and biomarker overrides before model execution.
    """
    audit_service.record_event(
        AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.RISK_ASSESSMENT_EXECUTION,
            actor_id="risk-assessment-gateway",
            resource_id=request.patient_id,
            action="validate_risk_request",
            status="success",
            metadata={"domain": request.domain, "horizon": request.prediction_horizon},
        )
    )

    return {
        "status": "ready_for_inference",
        "patient_id": request.patient_id,
        "domain": request.domain,
        "prediction_horizon": request.prediction_horizon,
        "overrides_count": len(request.custom_biomarker_overrides) if request.custom_biomarker_overrides else 0,
        "message": "Risk request parameters validated against clinical domain constraints.",
    }
