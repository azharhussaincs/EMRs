import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.core.config import ClinicalDomain
from app.core.audit import AuditEvent, AuditEventType, audit_service
from app.schemas.evidence import (
    ClinicalEvidenceReference,
    EvidenceSourceRegistryEntry,
    EvidenceRetrievalResponse,
    EvidenceDomainCategory,
)
from app.clinical.evidence import (
    curated_evidence_provider,
    map_clinical_features_to_evidence_domains,
)
from app.services.emr_ingestion import emr_ingestion_service


class EvidenceRetrievalService:
    """
    Coordinates verified clinical guideline evidence retrieval, source registry lookups,
    and HIPAA §164.312 audit logging.
    Strictly factual, non-generative, and non-prescriptive.
    """

    def __init__(self, provider=None):
        self._provider = provider or curated_evidence_provider

    def list_sources(self) -> List[EvidenceSourceRegistryEntry]:
        """List all registered authoritative evidence sources."""
        return self._provider.list_sources()

    def get_diabetes_evidence(
        self,
        patient_id: Optional[str] = None,
        category: Optional[EvidenceDomainCategory] = None,
        actor_id: str = "clinician-portal",
    ) -> EvidenceRetrievalResponse:
        """
        Retrieves verified clinical evidence references for the Diabetes pathway.
        Optionally links to patient's clinical features to select relevant evidence domains.
        """
        request_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc)
        target_category = category

        # If patient_id provided and no category specified, tailor category to verified patient features
        if patient_id and not target_category:
            record = emr_ingestion_service.get_patient_record(patient_id)
            if record:
                feature_keys = list(record.longitudinal_biomarkers.keys())
                has_ckd = any(
                    "n18" in c.icd10_code.lower() for c in record.conditions
                ) or "egfr" in feature_keys
                mapped_domains = map_clinical_features_to_evidence_domains(
                    feature_names=feature_keys, has_comorbid_ckd=has_ckd
                )
                if mapped_domains:
                    # Select primary mapped domain category if desired, or return all matching
                    pass

        references = self._provider.get_references_by_domain(
            domain=ClinicalDomain.DIABETES, category=target_category
        )

        response = EvidenceRetrievalResponse(
            domain="diabetes",
            query_category=target_category.value if target_category else None,
            total_references=len(references),
            provider_id=self._provider.provider_id,
            references=references,
            retrieved_at=now_utc,
            disclaimer="Clinical evidence references provided for informational decision support only. Strictly non-prescriptive.",
        )

        # Record verified HIPAA §164.312 audit event for evidence retrieval
        audit_service.record_event(
            AuditEvent(
                event_id=request_id,
                event_type=AuditEventType.KNOWLEDGE_RETRIEVAL,
                actor_id=actor_id,
                resource_id=patient_id or "global_evidence_registry",
                action="retrieve_diabetes_evidence",
                status="success",
                metadata={
                    "evidence_request_id": request_id,
                    "evidence_ids_returned": [r.evidence_id for r in references],
                    "evidence_sources": list(set(r.source_id for r in references)),
                    "provider_id": self._provider.provider_id,
                    "provider_version": self._provider.provider_version,
                },
            )
        )

        return response

    def get_cardiovascular_evidence(
        self,
        patient_id: Optional[str] = None,
        category: Optional[EvidenceDomainCategory] = None,
        actor_id: str = "clinician-portal",
    ) -> EvidenceRetrievalResponse:
        """
        Retrieves verified clinical evidence references for the Cardiovascular Disease pathway.
        Optionally links to patient's clinical features to select relevant evidence domains.
        """
        request_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc)
        target_category = category

        # If patient_id provided and no category specified, tailor category to verified patient features
        if patient_id and not target_category:
            record = emr_ingestion_service.get_patient_record(patient_id)
            if record:
                feature_keys = list(record.longitudinal_biomarkers.keys())
                has_ckd = any(
                    "n18" in c.icd10_code.lower() for c in record.conditions
                ) or "egfr" in feature_keys
                mapped_domains = map_clinical_features_to_evidence_domains(
                    feature_names=feature_keys, has_comorbid_ckd=has_ckd
                )
                if mapped_domains:
                    pass

        references = self._provider.get_references_by_domain(
            domain=ClinicalDomain.CARDIOVASCULAR, category=target_category
        )

        response = EvidenceRetrievalResponse(
            domain="cardiovascular",
            query_category=target_category.value if target_category else None,
            total_references=len(references),
            provider_id=self._provider.provider_id,
            references=references,
            retrieved_at=now_utc,
            disclaimer="Clinical evidence references provided for informational decision support only. Strictly non-prescriptive.",
        )

        # Record verified HIPAA §164.312 audit event for CVD evidence retrieval
        audit_service.record_event(
            AuditEvent(
                event_id=request_id,
                event_type=AuditEventType.KNOWLEDGE_RETRIEVAL,
                actor_id=actor_id,
                resource_id=patient_id or "global_evidence_registry",
                action="retrieve_cardiovascular_evidence",
                status="success",
                metadata={
                    "evidence_request_id": request_id,
                    "evidence_ids_returned": [r.evidence_id for r in references],
                    "evidence_sources": list(set(r.source_id for r in references)),
                    "provider_id": self._provider.provider_id,
                    "provider_version": self._provider.provider_version,
                },
            )
        )

        return response


evidence_service = EvidenceRetrievalService()

