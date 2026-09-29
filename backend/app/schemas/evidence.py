from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.config import ClinicalDomain


class EvidenceStatus(str, Enum):
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"


class EvidenceDomainCategory(str, Enum):
    HBA1C_MONITORING = "hba1c_monitoring"
    GLYCEMIC_TRAJECTORY_ASSESSMENT = "glycemic_trajectory_assessment"
    DIABETES_CLASSIFICATION_CONTEXT = "diabetes_classification_context"
    DIABETES_CKD_INTERSECTION = "diabetes_ckd_intersection"
    CARDIOVASCULAR_RISK_EXPANSION = "cardiovascular_risk_expansion"


class EvidenceSourceRegistryEntry(BaseModel):
    """
    Authoritative evidence source registry entry.
    Contains real, verifiable publication metadata strictly verified against official clinical bodies.
    """
    source_id: str = Field(..., description="Unique source identifier (e.g. ADA-SOC-2026)")
    organization: str = Field(..., description="Authoritative clinical organization (e.g. ADA, KDIGO, ACC/AHA)")
    title: str = Field(..., description="Official title of the clinical guideline")
    edition_year: int = Field(..., description="Publication year")
    guideline_identifier: Optional[str] = Field(None, description="Official publication or guideline identifier")
    official_url: str = Field(..., description="Verified primary URL for the published guideline")
    domain: ClinicalDomain = Field(..., description="Primary clinical disease domain")
    publication_status: str = Field(..., description="published_current | under_development | archived")
    retrieval_date: str = Field(..., description="ISO date of guideline verification")
    citation_metadata: str = Field(..., description="Formal bibliographic citation string")


class ClinicalEvidenceReference(BaseModel):
    """
    Typed clinical evidence reference model.
    Distinguishes verified metadata from unavailable metadata without fabricating citations or recommendation IDs.
    """
    evidence_id: str = Field(..., description="Unique evidence reference identifier (e.g. ev-ada-2026-glycemic-targets)")
    source_id: str = Field(..., description="Foreign key reference to EvidenceSourceRegistryEntry.source_id")
    organization: str = Field(..., description="Authoritative clinical publishing organization")
    guideline_title: str = Field(..., description="Title of the source clinical guideline")
    publication_version: str = Field(..., description="Publication edition or version string (e.g. '2026 Edition')")
    section_chapter: Optional[str] = Field(
        None, description="Verified guideline chapter or section name; None if not verified"
    )
    recommendation_identifier: Optional[str] = Field(
        None, description="Verified recommendation number if explicitly documented; None if unavailable"
    )
    citation_text: str = Field(..., description="Verified bibliographic citation string")
    official_url: str = Field(..., description="Verified reference URL")
    evidence_status: EvidenceStatus = Field(..., description="verified | unavailable")
    domain_category: EvidenceDomainCategory = Field(..., description="Clinical evidence domain categorization")
    scope_description: str = Field(..., description="Clinical scope of the evidence reference (non-prescriptive)")
    retrieved_at: datetime = Field(..., description="UTC timestamp of retrieval")


class EvidenceRetrievalResponse(BaseModel):
    """
    Container response for retrieved clinical evidence references.
    """
    domain: str = Field(..., description="Clinical domain evaluated (e.g. diabetes)")
    query_category: Optional[str] = Field(None, description="Specific evidence domain category queried")
    total_references: int = Field(..., ge=0, description="Total verified evidence references returned")
    provider_id: str = Field(..., description="Identifier of the evidence provider implementation")
    references: List[ClinicalEvidenceReference] = Field(default_factory=list)
    retrieved_at: datetime = Field(..., description="UTC timestamp of retrieval")
    disclaimer: str = Field(
        default="Clinical evidence references provided for informational decision support only. Strictly non-prescriptive.",
        description="Mandatory evidence boundary disclaimer",
    )
