from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone

from app.core.config import ClinicalDomain
from app.schemas.evidence import (
    EvidenceSourceRegistryEntry,
    ClinicalEvidenceReference,
    EvidenceDomainCategory,
)
from app.clinical.evidence.registry import (
    EVIDENCE_SOURCE_REGISTRY,
    VERIFIED_EVIDENCE_REFERENCES,
)


class ClinicalEvidenceProvider(ABC):
    """
    Abstract interface for clinical evidence retrieval providers.
    Supports future expansion to vector indices, official guideline APIs, or document retrievers.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @property
    @abstractmethod
    def provider_version(self) -> str:
        pass

    @abstractmethod
    def list_sources(self) -> List[EvidenceSourceRegistryEntry]:
        """List registered authoritative clinical evidence sources."""
        pass

    @abstractmethod
    def get_references_by_domain(
        self,
        domain: ClinicalDomain,
        category: Optional[EvidenceDomainCategory] = None,
    ) -> List[ClinicalEvidenceReference]:
        """Retrieve verified evidence references for a domain and optional category."""
        pass

    @abstractmethod
    def get_reference_by_id(
        self, evidence_id: str
    ) -> Optional[ClinicalEvidenceReference]:
        """Lookup specific evidence reference by unique identifier."""
        pass


class CuratedClinicalEvidenceProvider(ClinicalEvidenceProvider):
    """
    Deterministic, curated clinical evidence provider.
    Retrieves only strictly verified publication citations and metadata from official consensus bodies.
    Prohibits hallucinated citations or fabricated recommendation identifiers.
    """

    @property
    def provider_id(self) -> str:
        return "curated_evidence_provider_v1"

    @property
    def provider_version(self) -> str:
        return "1.0.0-foundation"

    def list_sources(self) -> List[EvidenceSourceRegistryEntry]:
        return list(EVIDENCE_SOURCE_REGISTRY.values())

    def get_references_by_domain(
        self,
        domain: ClinicalDomain,
        category: Optional[EvidenceDomainCategory] = None,
    ) -> List[ClinicalEvidenceReference]:
        results: List[ClinicalEvidenceReference] = []

        for ref in VERIFIED_EVIDENCE_REFERENCES:
            source = EVIDENCE_SOURCE_REGISTRY.get(ref.source_id)
            if not source:
                continue

            # Check domain matching (or cross-domain intersections like Diabetes-CKD)
            matches_domain = (source.domain == domain) or (
                domain == ClinicalDomain.DIABETES
                and ref.domain_category == EvidenceDomainCategory.DIABETES_CKD_INTERSECTION
            )

            if matches_domain:
                if category is None or ref.domain_category == category:
                    results.append(ref)

        return results

    def get_reference_by_id(
        self, evidence_id: str
    ) -> Optional[ClinicalEvidenceReference]:
        for ref in VERIFIED_EVIDENCE_REFERENCES:
            if ref.evidence_id == evidence_id:
                return ref
        return None


curated_evidence_provider = CuratedClinicalEvidenceProvider()
