from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.schemas.emr import (
    EMRValidationResponse,
    EMRIngestionSuccessResponse,
    NormalizedPatientRecord,
)
from app.services.emr_ingestion import emr_ingestion_service

router = APIRouter()


@router.post(
    "/validate",
    response_model=EMRValidationResponse,
    summary="Validate FHIR R4 / EMR Payload",
    description="Validates syntactic, physiological, and clinical boundary constraints without persisting data.",
)
async def validate_emr(payload: Dict[str, Any]) -> EMRValidationResponse:
    """
    Accepts a FHIR R4 Bundle or direct de-identified clinical payload.
    Checks biomarker physiological plausibility, chronological validity, and ontology codes.
    """
    is_valid, parsed_payload, normalized_rec, errors, warnings = emr_ingestion_service.validate_raw(payload)

    pat_id = None
    obs_cnt = 0
    cond_cnt = 0
    med_cnt = 0
    notes_cnt = 0

    if parsed_payload:
        pat_id = parsed_payload.patient_id
        obs_cnt = len(parsed_payload.observations)
        cond_cnt = len(parsed_payload.conditions)
        med_cnt = len(parsed_payload.medications)
        notes_cnt = len(parsed_payload.clinical_notes)

    if not is_valid:
        return EMRValidationResponse(
            valid=False,
            patient_id=pat_id,
            errors=errors,
            warnings=warnings,
            observations_count=obs_cnt,
            conditions_count=cond_cnt,
            medications_count=med_cnt,
            clinical_notes_count=notes_cnt,
            message=f"Clinical validation failed with {len(errors)} error(s).",
        )

    return EMRValidationResponse(
        valid=True,
        patient_id=pat_id,
        errors=[],
        warnings=warnings,
        observations_count=obs_cnt,
        conditions_count=cond_cnt,
        medications_count=med_cnt,
        clinical_notes_count=notes_cnt,
        message="EMR record successfully validated against clinical and physiological boundaries.",
    )


@router.post(
    "/ingest",
    response_model=EMRIngestionSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest & Normalize De-Identified EMR",
    description="Ingests, normalizes, chronologically orders longitudinal biomarkers, and records an immutable HIPAA §164.312 audit event.",
)
async def ingest_emr(payload: Dict[str, Any], request: Request):
    """
    Ingests a FHIR R4 Bundle or de-identified EMR record.
    Returns HTTP 422 if clinical constraints (e.g. impossible blood pressure, impossible HbA1c) are violated.
    """
    actor_id = request.headers.get("X-Actor-ID", "clinician-portal")
    response, errors = emr_ingestion_service.ingest_record(payload, actor_id=actor_id)

    if errors:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_type": "EMRValidationError",
                "message": f"EMR ingestion rejected: {len(errors)} clinical constraint violation(s) detected.",
                "errors": [e.model_dump() for e in errors],
            },
        )

    return response


@router.get(
    "/patients",
    summary="List Ingested Patient Clinical Overviews",
)
async def list_patients() -> List[Dict[str, Any]]:
    """Returns overview of all validated patients in the clinical repository."""
    return emr_ingestion_service.list_ingested_patients()


@router.get(
    "/patients/{patient_id}",
    response_model=NormalizedPatientRecord,
    summary="Get Normalized Longitudinal Patient Record",
)
async def get_patient(patient_id: str) -> NormalizedPatientRecord:
    """Returns chronologically sorted longitudinal biomarker sequences and clinical history."""
    record = emr_ingestion_service.get_patient_record(patient_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found in clinical repository.",
        )
    return record


@router.get(
    "/patients/{patient_id}/features",
    summary="Extract Clinical Trajectory Features for Patient",
    description="Computes longitudinal trajectory metrics for HbA1c, eGFR, and Systolic BP.",
)
async def get_patient_features(patient_id: str, domain: str = "all") -> Dict[str, Any]:
    try:
        return emr_ingestion_service.extract_domain_features(patient_id=patient_id, domain_name=domain)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/sample-fhir",
    summary="Get Validated De-Identified Sample FHIR R4 Record",
    description="Returns an authentic, de-identified FHIR R4 Bundle with longitudinal vitals and labs for testing.",
)
async def get_sample_fhir_record() -> Dict[str, Any]:
    """
    Provides a standardized de-identified cardiometabolic & renal patient record for 1-click clinical verification.
    """
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "id": "bundle-cardiometabolic-longitudinal-01",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "PT-CARDIO-RENAL-508",
                    "gender": "male",
                    "birthDate": "1964-08-14"
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-dm2",
                    "clinicalStatus": { "coding": [{ "code": "active" }] },
                    "code": {
                        "coding": [{ "system": "http://hl7.org/fhir/sid/icd-10", "code": "E11.9", "display": "Type 2 diabetes mellitus without complications" }],
                        "text": "Type 2 diabetes mellitus"
                    },
                    "recordedDate": "2021-04-10"
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-htn",
                    "clinicalStatus": { "coding": [{ "code": "active" }] },
                    "code": {
                        "coding": [{ "system": "http://hl7.org/fhir/sid/icd-10", "code": "I10", "display": "Essential (primary) hypertension" }],
                        "text": "Essential hypertension"
                    },
                    "recordedDate": "2020-09-18"
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-ckd",
                    "clinicalStatus": { "coding": [{ "code": "active" }] },
                    "code": {
                        "coding": [{ "system": "http://hl7.org/fhir/sid/icd-10", "code": "N18.3", "display": "Chronic kidney disease, stage 3" }],
                        "text": "Chronic kidney disease, stage 3"
                    },
                    "recordedDate": "2023-02-14"
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-metformin",
                    "status": "active",
                    "medicationCodeableConcept": {
                        "coding": [{ "system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "6809", "display": "Metformin 500 MG Oral Tablet" }],
                        "text": "Metformin 500 MG"
                    },
                    "dosageInstruction": [{ "text": "500 mg orally twice daily with meals" }]
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "med-lisinopril",
                    "status": "active",
                    "medicationCodeableConcept": {
                        "coding": [{ "system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "29046", "display": "Lisinopril 10 MG Oral Tablet" }],
                        "text": "Lisinopril 10 MG"
                    },
                    "dosageInstruction": [{ "text": "10 mg orally once daily in the morning" }]
                }
            },
            # Longitudinal HbA1c (Point 1: 18 months ago)
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-hba1c-t1",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c" }], "text": "HbA1c" },
                    "effectiveDateTime": "2024-09-15T09:00:00Z",
                    "valueQuantity": { "value": 7.1, "unit": "%", "code": "%" },
                    "referenceRange": [{ "low": { "value": 4.0 }, "high": { "value": 5.6 } }]
                }
            },
            # Longitudinal HbA1c (Point 2: 9 months ago)
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-hba1c-t2",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c" }], "text": "HbA1c" },
                    "effectiveDateTime": "2025-06-12T09:15:00Z",
                    "valueQuantity": { "value": 7.6, "unit": "%", "code": "%" },
                    "referenceRange": [{ "low": { "value": 4.0 }, "high": { "value": 5.6 } }]
                }
            },
            # Longitudinal HbA1c (Point 3: Recent baseline)
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-hba1c-t3",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c" }], "text": "HbA1c" },
                    "effectiveDateTime": "2026-02-20T08:45:00Z",
                    "valueQuantity": { "value": 8.2, "unit": "%", "code": "%" },
                    "referenceRange": [{ "low": { "value": 4.0 }, "high": { "value": 5.6 } }]
                }
            },
            # Longitudinal eGFR (Point 1: 18 months ago)
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-egfr-t1",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "33914-3", "display": "eGFR (CKD-EPI)" }], "text": "eGFR" },
                    "effectiveDateTime": "2024-09-15T09:00:00Z",
                    "valueQuantity": { "value": 64.0, "unit": "mL/min/1.73m²" },
                    "referenceRange": [{ "low": { "value": 60.0 } }]
                }
            },
            # Longitudinal eGFR (Point 2: Recent baseline - showing decline)
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-egfr-t2",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "33914-3", "display": "eGFR (CKD-EPI)" }], "text": "eGFR" },
                    "effectiveDateTime": "2026-02-20T08:45:00Z",
                    "valueQuantity": { "value": 52.0, "unit": "mL/min/1.73m²" },
                    "referenceRange": [{ "low": { "value": 60.0 } }]
                }
            },
            # Serum Creatinine
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-creat-t2",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "2160-0", "display": "Creatinine [Mass/volume] in Blood" }], "text": "Serum Creatinine" },
                    "effectiveDateTime": "2026-02-20T08:45:00Z",
                    "valueQuantity": { "value": 1.45, "unit": "mg/dL" },
                    "referenceRange": [{ "low": { "value": 0.7 }, "high": { "value": 1.3 } }]
                }
            },
            # Blood Pressure Panel (Systolic + Diastolic)
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-bp-panel",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel" }] },
                    "effectiveDateTime": "2026-02-20T08:30:00Z",
                    "component": [
                        {
                            "code": { "coding": [{ "system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure" }] },
                            "valueQuantity": { "value": 142.0, "unit": "mmHg" }
                        },
                        {
                            "code": { "coding": [{ "system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure" }] },
                            "valueQuantity": { "value": 88.0, "unit": "mmHg" }
                        }
                    ]
                }
            },
            # Total Cholesterol
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-chol-t2",
                    "status": "final",
                    "code": { "coding": [{ "system": "http://loinc.org", "code": "2093-3", "display": "Cholesterol [Mass/volume] in Serum or Plasma" }], "text": "Total Cholesterol" },
                    "effectiveDateTime": "2026-02-20T08:45:00Z",
                    "valueQuantity": { "value": 218.0, "unit": "mg/dL" },
                    "referenceRange": [{ "high": { "value": 200.0 } }]
                }
            },
            # Clinical Consultation Note
            {
                "resource": {
                    "resourceType": "DocumentReference",
                    "id": "doc-consult-01",
                    "status": "current",
                    "date": "2026-02-20T10:00:00Z",
                    "type": { "text": "Endocrinology Outpatient Progress Note" },
                    "content": [
                        {
                            "attachment": {
                                "title": "Comprehensive cardiometabolic consultation note.",
                                "data": "Patient seen for annual glycemic and renal assessment. Noted upward drift in HbA1c to 8.2% despite metformin adherence. Estimated GFR dropped from 64 to 52 mL/min over 18 months, indicating Stage 3a CKD transition. Blood pressure elevated at 142/88 mmHg. Discussed adding SGLT2 inhibitor per ADA/KDIGO consensus guidelines for dual cardiorenal protection."
                            }
                        }
                    ]
                }
            }
        ]
    }
