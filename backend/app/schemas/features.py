from datetime import datetime
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field


class HbA1cTrajectoryFeature(BaseModel):
    available: bool = Field(..., description="Whether HbA1c data exists")
    status: str = Field(..., description="available | insufficient_history | single_measurement | identical_timestamps")
    measurement_count: int = 0
    latest_value: Optional[float] = None
    latest_timestamp: Optional[datetime] = None
    previous_value: Optional[float] = None
    previous_timestamp: Optional[datetime] = None
    absolute_change: Optional[float] = None
    time_interval_days: Optional[float] = None
    annualized_rate_of_change: Optional[float] = Field(
        None, description="Annualized rate of change (% / year) when sufficient distinct timestamps exist"
    )
    unit: str = "%"


class EGFRTrajectoryFeature(BaseModel):
    available: bool = Field(..., description="Whether eGFR data exists")
    status: str = Field(..., description="available | insufficient_history | single_measurement | identical_timestamps")
    measurement_count: int = 0
    latest_value: Optional[float] = None
    latest_timestamp: Optional[datetime] = None
    previous_value: Optional[float] = None
    previous_timestamp: Optional[datetime] = None
    absolute_change: Optional[float] = None
    time_interval_days: Optional[float] = None
    annualized_slope: Optional[float] = Field(
        None, description="Annualized eGFR slope (mL/min/1.73m² / year) when sufficient distinct timestamps exist"
    )
    unit: str = "mL/min/1.73m²"


class SystolicBPTrajectoryFeature(BaseModel):
    available: bool = Field(..., description="Whether systolic blood pressure data exists")
    status: str = Field(..., description="available | insufficient_history | single_measurement")
    measurement_count: int = 0
    latest_value: Optional[float] = None
    latest_timestamp: Optional[datetime] = None
    mean: Optional[float] = Field(None, description="Arithmetic mean of all systolic BP readings")
    standard_deviation: Optional[float] = Field(
        None, description="Sample standard deviation (variability) when n >= 2"
    )
    unit: str = "mmHg"


# --- Step 12: ASCVD / Cardiovascular Feature Models ---

class LipidBiomarkerFeature(BaseModel):
    available: bool = Field(..., description="Whether lipid measurement exists")
    status: str = Field(..., description="available | unavailable | single_measurement")
    measurement_count: int = 0
    latest_value: Optional[float] = None
    latest_timestamp: Optional[datetime] = None
    previous_value: Optional[float] = None
    previous_timestamp: Optional[datetime] = None
    unit: str = "mg/dL"


class SmokingStatusFeature(BaseModel):
    available: bool = Field(..., description="Whether smoking status is explicitly documented")
    status: str = Field(..., description="available | unavailable")
    value: Optional[str] = Field(
        None, description="Documented status: current_smoker | former_smoker | never_smoker"
    )
    source_code: Optional[str] = Field(None, description="Ontology concept or ICD-10 code (e.g. F17.2, Z87.891)")
    source_display: Optional[str] = None
    documented_date: Optional[str] = None


class DiabetesHistoryFeature(BaseModel):
    available: bool = Field(..., description="Whether diabetes clinical status is evaluated")
    status: str = Field(..., description="available | unavailable")
    has_diabetes: Optional[bool] = Field(
        None, description="True if documented in conditions, medications, or lab criteria"
    )
    source_evidence: List[str] = Field(
        default_factory=list, description="Explicit clinical evidence references supporting status"
    )
    documented_date: Optional[str] = None


class ASCVDClinicalFeatures(BaseModel):
    patient_id: str
    extracted_at: datetime
    age_years: Optional[int] = Field(None, description="Patient age in years; None if birth_date missing")
    age_available: bool = False
    gender: Optional[str] = Field(None, description="Administrative sex: male | female | other; None if missing")
    gender_available: bool = False
    systolic_bp: SystolicBPTrajectoryFeature
    total_cholesterol: LipidBiomarkerFeature
    hdl_cholesterol: LipidBiomarkerFeature
    smoking_status: SmokingStatusFeature
    diabetes_history: DiabetesHistoryFeature
    missing_required_features: List[str] = Field(
        default_factory=list,
        description="List of primary ASCVD calculator features missing from record"
    )
    is_sufficient_for_ascvd: bool = Field(
        default=False,
        description="True if all core ASCVD features are present without imputation"
    )


class ClinicalDomainFeatures(BaseModel):
    patient_id: str
    domain: str
    extracted_at: datetime
    hba1c: HbA1cTrajectoryFeature
    egfr: EGFRTrajectoryFeature
    systolic_bp: SystolicBPTrajectoryFeature
    ascvd: Optional[ASCVDClinicalFeatures] = Field(
        default=None, description="Structured ASCVD clinical risk factor features"
    )
    feature_vector: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Deterministic flat feature mapping for model pipelines"
    )
