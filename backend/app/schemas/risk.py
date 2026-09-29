from datetime import datetime
from enum import Enum
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


# --- Step 5 Extensible Risk Assessment Contract ---

class DataSufficiencyStatus(str, Enum):
    SUFFICIENT = "sufficient_data"
    INSUFFICIENT = "insufficient_data"
    UNAVAILABLE = "unavailable_feature"


class CalibrationStatus(str, Enum):
    NOT_CALIBRATED = "not_calibrated"
    CALIBRATED = "calibrated"
    INSUFFICIENT_MODEL = "insufficient_model"


class ConfidenceInterval(BaseModel):
    low: Optional[float] = Field(None, ge=0.0, le=1.0, description="Lower bound of probability interval")
    high: Optional[float] = Field(None, ge=0.0, le=1.0, description="Upper bound of probability interval")
    confidence_level: float = Field(0.95, description="Statistical confidence level, e.g. 0.95")


class UsedFeatureValue(BaseModel):
    feature_name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    description: str


class RiskAssessmentResult(BaseModel):
    """
    Extensible, strongly typed risk assessment contract for multi-disease stratification.
    Extensible across: Diabetes, Cardiovascular Disease, Chronic Kidney Disease, Cancer.
    """
    assessment_id: str = Field(..., description="Unique assessment event identifier")
    patient_id: str = Field(..., description="Pseudonymous patient identifier")
    assessed_at: datetime = Field(..., description="UTC timestamp of evaluation")
    domain: ClinicalDomain = Field(..., description="Target disease domain")
    estimator_id: str = Field(..., description="Identifier of the specific estimator pipeline")
    estimator_version: str = Field(..., description="Semantic version of the estimator")
    data_sufficiency: DataSufficiencyStatus = Field(
        ..., description="sufficient_data | insufficient_data | unavailable_feature"
    )
    calibration_status: CalibrationStatus = Field(
        ..., description="not_calibrated | calibrated | insufficient_model"
    )
    risk_estimate: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Calibrated probability (0.0 to 1.0). Null if uncalibrated or data insufficient.",
    )
    confidence_interval: Optional[ConfidenceInterval] = Field(
        None, description="Statistical confidence interval when calibrated"
    )
    features_used: Dict[str, UsedFeatureValue] = Field(
        default_factory=dict, description="Named features and values utilized by the estimator"
    )
    unavailable_inputs: List[str] = Field(
        default_factory=list, description="List of expected domain inputs that were unavailable or insufficient"
    )
    limitations: List[str] = Field(
        default_factory=list, description="Explicit statistical, demographic, or data-completeness limitations"
    )
    disclaimer: str = Field(
        default="Research & engineering risk stratification prototype. Does not claim clinical diagnostic validity. Not an autonomous clinical diagnosis.",
        description="Mandatory regulatory and clinical decision boundary disclaimer",
    )
