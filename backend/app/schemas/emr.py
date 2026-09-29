from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ClinicalCoding(BaseModel):
    system: Optional[str] = Field(None, description="Ontology URI (e.g. http://loinc.org, http://hl7.org/fhir/sid/icd-10)")
    code: str = Field(..., description="Machine-readable ontology code")
    display: Optional[str] = Field(None, description="Human-readable concept name")


class EMRObservation(BaseModel):
    observation_id: str = Field(..., description="Unique observation identifier")
    code: ClinicalCoding
    effective_datetime: datetime = Field(..., description="Timestamp of observation measurement")
    value_numeric: Optional[float] = None
    value_string: Optional[str] = None
    unit: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None


class EMRCondition(BaseModel):
    condition_id: str = Field(..., description="Unique condition identifier")
    code: ClinicalCoding
    clinical_status: str = Field(default="active", description="active | recurrence | relapse | inactive | resolved")
    verification_status: str = Field(default="confirmed", description="unconfirmed | provisional | differential | confirmed")
    recorded_date: Optional[date] = None


class EMRMedication(BaseModel):
    medication_id: str
    code: Optional[ClinicalCoding] = None
    display_name: str
    status: str = Field(default="active", description="active | completed | entered-in-error | stopped")
    dosage_instruction: Optional[str] = None
    start_date: Optional[date] = None


class EMRClinicalNote(BaseModel):
    note_id: str
    note_type: str = Field(..., description="e.g. Progress Note, Discharge Summary, Outpatient Consult")
    created_at: datetime
    author_specialty: Optional[str] = None
    sanitized_text: str = Field(..., description="De-identified narrative clinical note content")


class PatientEMRPayload(BaseModel):
    patient_id: str = Field(..., description="Unique pseudonymous patient identifier")
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, description="Administrative sex: male | female | other | unknown")
    observations: List[EMRObservation] = Field(default_factory=list)
    conditions: List[EMRCondition] = Field(default_factory=list)
    medications: List[EMRMedication] = Field(default_factory=list)
    clinical_notes: List[EMRClinicalNote] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Validation Error Models ---
class ClinicalValidationErrorItem(BaseModel):
    field: str = Field(..., description="Path to invalid attribute, e.g. observations[2].value_numeric")
    issue: str = Field(..., description="Clinical reason for rejection")
    code: str = Field(..., description="Rejection error code")
    observed_value: Optional[Any] = None
    acceptable_range: Optional[str] = None


class EMRValidationResponse(BaseModel):
    valid: bool
    patient_id: Optional[str] = None
    errors: List[ClinicalValidationErrorItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    observations_count: int = 0
    conditions_count: int = 0
    medications_count: int = 0
    clinical_notes_count: int = 0
    message: str


# --- Normalized Internal Clinical Schema (Longitudinal) ---
class NormalizedBiomarkerPoint(BaseModel):
    observation_id: str
    biomarker_key: str
    standard_name: str
    effective_datetime: datetime
    value: float
    unit: str
    loinc_code: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None


class NormalizedCondition(BaseModel):
    condition_id: str
    icd10_code: str
    display_name: str
    clinical_status: str
    recorded_date: Optional[date] = None


class NormalizedMedication(BaseModel):
    medication_id: str
    display_name: str
    rxnorm_code: Optional[str] = None
    dosage_instruction: Optional[str] = None
    status: str


class NormalizedClinicalNote(BaseModel):
    note_id: str
    note_type: str
    created_at: datetime
    author_specialty: Optional[str] = None
    text_preview: str


class NormalizedPatientRecord(BaseModel):
    patient_id: str
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    age_years: Optional[int] = None
    longitudinal_biomarkers: Dict[str, List[NormalizedBiomarkerPoint]] = Field(
        default_factory=dict,
        description="Chronologically sorted biomarker sequences mapped by biomarker_key"
    )
    conditions: List[NormalizedCondition] = Field(default_factory=list)
    medications: List[NormalizedMedication] = Field(default_factory=list)
    clinical_notes: List[NormalizedClinicalNote] = Field(default_factory=list)
    clinical_domain_readiness: Dict[str, bool] = Field(
        default_factory=dict,
        description="Flag indicating if baseline data is present for: diabetes, cardiovascular, chronic_kidney_disease, cancer"
    )
    total_biomarker_measurements: int = 0
    earliest_record_date: Optional[datetime] = None
    latest_record_date: Optional[datetime] = None


class EMRIngestionSuccessResponse(BaseModel):
    status: str = "ingested"
    ingestion_id: str
    audit_event_id: str
    patient_record: NormalizedPatientRecord
    received_at: datetime
