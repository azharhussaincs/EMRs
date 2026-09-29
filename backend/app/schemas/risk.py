from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.config import ClinicalDomain, RiskTier


class BiomarkerFeatureImpact(BaseModel):
    feature_name: str
    measured_value: Optional[float] = None
    unit: Optional[str] = None
    clinical_reference_range: Optional[str] = None
    impact_direction: str = Field(..., description="increases_risk | decreases_risk | neutral")
    relative_weight: float = Field(..., ge=0.0, le=1.0, description="Normalized feature attribution weight")


class RiskAssessmentRequest(BaseModel):
    patient_id: str = Field(..., description="Pseudonymous patient identifier")
    domain: ClinicalDomain = Field(..., description="Target disease risk area")
    prediction_horizon: str = Field(default="5-year", description="Temporal prediction window")
    custom_biomarker_overrides: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional simulation overrides for hypothetical clinical intervention testing"
    )


class RiskAssessmentResponse(BaseModel):
    assessment_id: str
    patient_id: str
    domain: ClinicalDomain
    prediction_horizon: str
    calibrated_risk_score: float = Field(..., ge=0.0, le=1.0, description="Calibrated empirical probability (0.0 to 1.0)")
    risk_tier: RiskTier
    confidence_interval_low: float = Field(..., ge=0.0, le=1.0)
    confidence_interval_high: float = Field(..., ge=0.0, le=1.0)
    top_contributing_biomarkers: List[BiomarkerFeatureImpact]
    model_version: str
    model_card_uri: Optional[str] = None
    calculated_at: datetime
    clinician_actionable_window_days: int
