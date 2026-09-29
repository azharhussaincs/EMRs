from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ClinicalCoding(BaseModel):
    system: str = Field(..., description="Ontology URI (e.g., http://loinc.org, http://hl7.org/fhir/sid/icd-10)")
    code: str = Field(..., description="Machine-readable code")
    display: Optional[str] = Field(None, description="Human-readable concept name")


class EMRObservation(BaseModel):
    observation_id: str
    code: ClinicalCoding
    effective_datetime: datetime
    value_numeric: Optional[float] = None
    value_string: Optional[str] = None
    unit: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None


class EMRCondition(BaseModel):
    condition_id: str
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
    note_type: str = Field(..., description="e.g. Progress Note, Discharge Summary, Cardiology Consult")
    created_at: datetime
    author_specialty: Optional[str] = None
    sanitized_text: str = Field(..., description="De-identified narrative clinical note content")


class PatientEMRPayload(BaseModel):
    patient_id: str = Field(..., description="Unique pseudonymous patient identifier")
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, description="administrative sex: male | female | other | unknown")
    observations: List[EMRObservation] = Field(default_factory=list)
    conditions: List[EMRCondition] = Field(default_factory=list)
    medications: List[EMRMedication] = Field(default_factory=list)
    clinical_notes: List[EMRClinicalNote] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EMRIngestionResponse(BaseModel):
    ingestion_id: str
    patient_id: str
    status: str = "received"
    total_observations: int
    total_conditions: int
    total_medications: int
    total_clinical_notes: int
    received_at: datetime
