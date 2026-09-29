import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from app.core.config import ClinicalDomain
from app.core.audit import AuditEvent, AuditEventType, audit_service
from app.schemas.risk import RiskAssessmentRequest

router = APIRouter()


@router.get("/capabilities", summary="List Registered Predictive Model Capabilities")
async def list_model_capabilities() -> Dict[str, Any]:
    """
    Returns metadata regarding the risk prediction pipelines designed for each clinical domain.
    """
    return {
        "engine_architecture": "Modular Multi-Disease Clinical Risk Ensemble",
        "supported_domains": [d.value for d in ClinicalDomain],
        "feature_stores": {
            "time_series_vitals": "LOINC-coded longitudinal physiological measurements",
            "laboratory_panels": "Standard metabolic, lipid, and biomarker indices",
            "clinical_covariates": "Age, biological sex, comorbidity history",
        },
        "model_status": "pipeline_interface_ready",
        "notes": "Predictive model weights and calibrated cohorts to be wired in subsequent modeling phase.",
    }


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
