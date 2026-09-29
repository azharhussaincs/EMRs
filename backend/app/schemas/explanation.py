from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.config import ClinicalDomain
from app.schemas.risk import DataSufficiencyStatus, CalibrationStatus


class ExplanationBiomarkerFact(BaseModel):
    """
    Factual, verified biomarker observation or derived measurement.
    Strictly prohibits unverified or synthetic clinical values.
    """
    feature_name: str = Field(..., description="Canonical feature key (e.g. hba1c_latest)")
    is_available: bool = Field(..., description="Whether the measurement is present in patient EMR")
    value: Optional[float] = Field(None, description="Numeric measured or derived value; None if unavailable")
    unit: Optional[str] = Field(None, description="Standard clinical unit (e.g. %, %/year)")
    source_timestamp: Optional[datetime] = Field(None, description="Timestamp of underlying observation if applicable")
    description: str = Field(..., description="Clinical definition of the measured parameter")


class ExplanationTrajectorySummary(BaseModel):
    """
    Longitudinal trajectory summary preserving chronological history.
    """
    measurement_count: int = Field(..., ge=0, description="Total number of historical observations")
    latest_timestamp: Optional[datetime] = Field(None, description="Timestamp of most recent measurement")
    previous_timestamp: Optional[datetime] = Field(None, description="Timestamp of preceding comparison measurement")
    time_interval_days: Optional[float] = Field(None, ge=0.0, description="Temporal interval in days between observations")
    trajectory_direction: str = Field(
        ...,
        description="Factual trajectory trend: 'increasing' | 'decreasing' | 'stable' | 'insufficient_history' | 'unavailable'"
    )
    annualized_rate: Optional[float] = Field(None, description="Annualized progression rate (%/year)")
    annualized_rate_unit: str = Field(default="%/year")


class AIExplanationContext(BaseModel):
    """
    Safe, deterministic clinical explanation context layer for GenAI narrative synthesis.
    Contains ONLY verified facts and derived measurements produced by the EMR and risk engine.
    
    CRITICAL CLINICAL SAFETY BOUNDARIES:
    - Contains no invented clinical facts or hallucinated metrics.
    - Contains no unsupported diagnostic claims.
    - Contains no treatment directives, medication changes, or dosage recommendations.
    - Prohibits fabricated risk probabilities or artificial confidence intervals.
    """
    # Context Identifiers & Audit Traceability
    context_id: str = Field(..., description="Unique explanation context execution identifier")
    patient_id: str = Field(..., description="Pseudonymous patient identifier")
    assessment_id: str = Field(..., description="Reference to source RiskAssessmentResult")
    domain: ClinicalDomain = Field(..., description="Target clinical disease area")
    context_generated_at: datetime = Field(..., description="UTC timestamp of context extraction")
    assessment_timestamp: datetime = Field(..., description="UTC timestamp when assessment was generated")
    estimator_id: str = Field(..., description="Estimator pipeline identifier")
    estimator_version: str = Field(..., description="Semantic version of the estimator")

    # Data Quality & Calibration Status
    data_sufficiency: DataSufficiencyStatus = Field(..., description="sufficient_data | insufficient_data | unavailable_feature")
    calibration_status: CalibrationStatus = Field(..., description="not_calibrated | calibrated | insufficient_model")
    calibrated_risk_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Calibrated empirical probability (0.0 to 1.0). Strictly None when uncalibrated."
    )
    is_statistically_calibrated: bool = Field(
        default=False,
        description="Whether a calibrated probability is statistically valid"
    )

    # Verified Factual Glycemic Trajectory (Diabetes Pathway)
    latest_hba1c: ExplanationBiomarkerFact
    previous_hba1c: ExplanationBiomarkerFact
    absolute_change: ExplanationBiomarkerFact
    annualized_rate: ExplanationBiomarkerFact
    trajectory_summary: ExplanationTrajectorySummary

    # Completeness & Limitations
    source_features_used: List[str] = Field(default_factory=list, description="Verified feature keys utilized")
    unavailable_inputs: List[str] = Field(default_factory=list, description="Expected domain inputs that were unavailable")
    documented_limitations: List[str] = Field(default_factory=list, description="Explicit statistical and data limitations")

    # Regulatory & Clinical Decision Boundaries
    is_diagnostic_claim: bool = Field(
        default=False,
        description="Safety flag: strictly prohibits autonomous diagnostic statements"
    )
    treatment_recommendations_allowed: bool = Field(
        default=False,
        description="Safety flag: strictly prohibits autonomous medication/therapy directives"
    )
    non_diagnostic_disclaimer: str = Field(
        default="Factual clinical explanation context for decision support only. Strictly non-diagnostic and non-prescriptive. Requires review and verification by a licensed healthcare clinician.",
        description="Mandatory clinical safety boundary disclaimer"
    )


class ASCVDExplanationContext(BaseModel):
    """
    Deterministic clinical explanation context layer for Cardiovascular Disease / ASCVD.
    Contains ONLY verified clinical observations and mathematically derived trajectory features.

    CRITICAL CLINICAL SAFETY BOUNDARIES:
    - Contains no invented clinical facts or hallucinated metrics.
    - Prohibits fabricated risk probabilities or artificial confidence intervals (strictly None when uncalibrated).
    - Prohibits autonomous diagnostic claims (is_diagnostic_claim = False).
    - Prohibits medication/statin directives or dosage recommendations (treatment_recommendations_allowed = False).
    - Preserves unmeasured parameters as unavailable without synthetic imputation.
    """
    # Context Identifiers & Traceability
    context_id: str = Field(..., description="Unique explanation context execution identifier")
    patient_id: str = Field(..., description="Pseudonymous patient identifier")
    assessment_id: str = Field(..., description="Reference to source RiskAssessmentResult")
    domain: ClinicalDomain = Field(default=ClinicalDomain.CARDIOVASCULAR, description="Clinical domain")
    context_generated_at: datetime = Field(..., description="UTC timestamp of context extraction")
    assessment_timestamp: datetime = Field(..., description="UTC timestamp when assessment was generated")
    estimator_id: str = Field(..., description="Estimator pipeline identifier")
    estimator_version: str = Field(..., description="Semantic version of the estimator")

    # Data Quality & Calibration Status
    data_sufficiency: DataSufficiencyStatus = Field(..., description="sufficient_data | insufficient_data | unavailable_feature")
    calibration_status: CalibrationStatus = Field(..., description="not_calibrated | calibrated | insufficient_model")
    calibrated_risk_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Calibrated empirical probability (0.0 to 1.0). Strictly None when uncalibrated."
    )
    is_statistically_calibrated: bool = Field(
        default=False,
        description="Whether a calibrated probability is statistically valid"
    )

    # Core ASCVD Clinical Risk Factors (Ground Truth)
    age_years: Optional[int] = Field(None, description="Patient age in years; None if missing")
    age_available: bool = Field(default=False, description="Whether age is documented")
    gender: Optional[str] = Field(None, description="Administrative sex: male | female | other; None if missing")
    gender_available: bool = Field(default=False, description="Whether sex/gender is documented")

    # Blood Pressure Fact & Trajectory
    systolic_bp: ExplanationBiomarkerFact = Field(..., description="Latest resting systolic blood pressure")
    systolic_bp_mean: Optional[float] = Field(None, description="Arithmetic mean of all systolic BP readings")
    systolic_bp_std: Optional[float] = Field(None, description="Sample standard deviation of systolic BP readings")
    systolic_bp_count: int = Field(default=0, ge=0, description="Total number of historical systolic BP readings")

    # Lipid Biomarker Facts
    total_cholesterol: ExplanationBiomarkerFact = Field(..., description="Latest total serum cholesterol")
    hdl_cholesterol: ExplanationBiomarkerFact = Field(..., description="Latest high-density lipoprotein cholesterol")

    # Clinical History & Lifestyle Factors
    smoking_status: Optional[str] = Field(None, description="Documented smoking status: current_smoker | former_smoker | never_smoker")
    smoking_status_available: bool = Field(default=False, description="Whether smoking status is explicitly documented")
    smoking_status_code: Optional[str] = Field(None, description="Ontology or ICD-10 code for smoking status")

    has_diabetes: Optional[bool] = Field(None, description="Whether patient has documented diabetes history")
    diabetes_status_available: bool = Field(default=False, description="Whether diabetes history is evaluated")
    diabetes_source_evidence: List[str] = Field(default_factory=list, description="Explicit clinical evidence supporting diabetes status")

    # Completeness & Limitations
    source_features_used: List[str] = Field(default_factory=list, description="Verified feature keys utilized")
    unavailable_inputs: List[str] = Field(default_factory=list, description="Expected domain inputs that were unavailable")
    documented_limitations: List[str] = Field(default_factory=list, description="Explicit statistical and data limitations")

    # Regulatory & Clinical Decision Boundaries
    is_diagnostic_claim: bool = Field(
        default=False,
        description="Safety flag: strictly prohibits autonomous diagnostic statements"
    )
    treatment_recommendations_allowed: bool = Field(
        default=False,
        description="Safety flag: strictly prohibits autonomous medication/therapy directives (including statins)"
    )
    non_diagnostic_disclaimer: str = Field(
        default="Factual clinical explanation context for decision support only. Strictly non-diagnostic and non-prescriptive. Requires review and verification by a licensed healthcare clinician.",
        description="Mandatory clinical safety boundary disclaimer"
    )

