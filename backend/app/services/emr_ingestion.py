import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.clinical.features import extract_clinical_features
from app.clinical.fhir_parser import FHIRClinicalParser, ClinicalSemanticValidator
from app.core.audit import AuditEvent, AuditEventType, audit_service
from app.core.exceptions import EMRValidationError
from app.schemas.emr import (
    PatientEMRPayload,
    ClinicalValidationErrorItem,
    EMRValidationResponse,
    NormalizedPatientRecord,
    EMRIngestionSuccessResponse,
)
from app.schemas.features import ClinicalDomainFeatures


class BaseEMRIngestionService(ABC):
    """
    Abstract interface for EMR ingestion adapters and feature extraction points.
    """

    @abstractmethod
    def extract_domain_features(self, patient_id: str, domain_name: str = "all") -> Dict[str, Any]:
        """Extract domain-relevant clinical biomarker trajectory features from patient EMR record."""
        pass


class EMRIngestionService(BaseEMRIngestionService):
    """
    Production-grade service managing FHIR R4 and EMR ingestion, validation,
    normalization, clinical repository persistence, and trajectory feature derivation.
    """

    def __init__(self):
        # In-memory storage for ingested normalized patient records (keyed by patient_id)
        self._patient_repository: Dict[str, NormalizedPatientRecord] = {}

    def validate_raw(
        self, raw_payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[PatientEMRPayload], Optional[NormalizedPatientRecord], List[ClinicalValidationErrorItem], List[str]]:
        """
        Parses raw JSON (FHIR Bundle or direct schema), runs clinical semantic validation,
        and returns validation state without modifying repository.
        """
        parsed_payload, parse_errors = FHIRClinicalParser.parse_raw_payload(raw_payload)
        if parse_errors:
            return False, parsed_payload, None, parse_errors, []

        normalized_rec, semantic_errors, warnings = ClinicalSemanticValidator.validate_and_normalize(parsed_payload)
        if semantic_errors or not normalized_rec:
            return False, parsed_payload, None, semantic_errors, warnings

        return True, parsed_payload, normalized_rec, [], warnings

    def ingest_record(
        self, raw_payload: Dict[str, Any], actor_id: str = "clinician-portal"
    ) -> Tuple[Optional[EMRIngestionSuccessResponse], Optional[List[ClinicalValidationErrorItem]]]:
        """
        Validates, normalizes, registers an immutable HIPAA audit event, and stores
        the normalized clinical record.
        """
        is_valid, parsed_payload, normalized_rec, errors, warnings = self.validate_raw(raw_payload)

        if not is_valid or not normalized_rec:
            # Audit failed ingestion attempt
            pat_id = getattr(parsed_payload, "patient_id", "UNKNOWN") if parsed_payload else "UNKNOWN"
            audit_service.record_event(
                AuditEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=AuditEventType.EMR_INGESTION,
                    actor_id=actor_id,
                    resource_id=pat_id,
                    action="emr_ingestion_rejected",
                    status="rejected",
                    metadata={
                        "error_count": len(errors),
                        "first_error": errors[0].issue if errors else "Validation failed",
                    },
                )
            )
            return None, errors

        # Store in clinical repository
        pat_id = normalized_rec.patient_id
        self._patient_repository[pat_id] = normalized_rec

        ingestion_id = f"ingest-{uuid.uuid4().hex[:12]}"
        audit_event_id = str(uuid.uuid4())

        # Record verified HIPAA §164.312 audit event
        audit_service.record_event(
            AuditEvent(
                event_id=audit_event_id,
                event_type=AuditEventType.EMR_INGESTION,
                actor_id=actor_id,
                resource_id=pat_id,
                action="ingest_patient_emr",
                status="success",
                metadata={
                    "ingestion_id": ingestion_id,
                    "measurements_count": normalized_rec.total_biomarker_measurements,
                    "conditions_count": len(normalized_rec.conditions),
                    "medications_count": len(normalized_rec.medications),
                    "notes_count": len(normalized_rec.clinical_notes),
                    "domain_readiness": normalized_rec.clinical_domain_readiness,
                },
            )
        )

        response = EMRIngestionSuccessResponse(
            status="ingested",
            ingestion_id=ingestion_id,
            audit_event_id=audit_event_id,
            patient_record=normalized_rec,
            received_at=datetime.now(timezone.utc),
        )

        return response, None

    def get_patient_record(self, patient_id: str) -> Optional[NormalizedPatientRecord]:
        """Retrieve stored normalized clinical record by pseudonymous patient ID."""
        return self._patient_repository.get(patient_id)

    def list_ingested_patients(self) -> List[Dict[str, Any]]:
        """List summary overview of all ingested patient records."""
        summaries = []
        for pat_id, rec in self._patient_repository.items():
            summaries.append({
                "patient_id": pat_id,
                "gender": rec.gender,
                "age_years": rec.age_years,
                "total_measurements": rec.total_biomarker_measurements,
                "conditions_count": len(rec.conditions),
                "medications_count": len(rec.medications),
                "domain_readiness": rec.clinical_domain_readiness,
            })
        return summaries

    def extract_domain_features(self, patient_id: str, domain_name: str = "all") -> Dict[str, Any]:
        """
        Implementation of BaseEMRIngestionService.extract_domain_features.
        Retrieves the normalized patient EMR and computes longitudinal trajectory features
        for HbA1c, eGFR, and Systolic Blood Pressure.
        """
        record = self.get_patient_record(patient_id)
        if not record:
            raise ValueError(f"Patient with identifier '{patient_id}' not found in clinical repository.")

        features = extract_clinical_features(record, domain=domain_name)
        return features.model_dump(mode="json")

    def extract_features_from_record(
        self, record: NormalizedPatientRecord, domain_name: str = "all"
    ) -> ClinicalDomainFeatures:
        """
        Convenience method to compute clinical trajectory features directly from
        a NormalizedPatientRecord without needing repository lookup.
        """
        return extract_clinical_features(record, domain=domain_name)


emr_ingestion_service = EMRIngestionService()
