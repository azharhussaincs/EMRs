from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.clinical.domains import ClinicalGuidelineReference


class TargetAudience(str, Enum):
    CLINICIAN = "clinician"
    PATIENT = "patient"


class ClinicalNarrativeRequest(BaseModel):
    assessment_id: str = Field(..., description="ID of completed validated risk assessment")
    target_audience: TargetAudience = Field(
        default=TargetAudience.CLINICIAN,
        description="Perspective tailoring: clinical jargon & differential logic vs plain language health literacy"
    )
    include_evidence_citations: bool = Field(default=True)
    specific_physician_notes: Optional[str] = Field(None, description="Clinician context or specific question")


class EvidenceCitation(BaseModel):
    source_guideline: str
    section: str
    recommendation_statement: str
    strength_of_recommendation: str
    doi_or_url: Optional[str] = None


class ClinicalNarrativeResponse(BaseModel):
    narrative_id: str
    assessment_id: str
    target_audience: TargetAudience
    executive_summary: str = Field(..., description="High-level synthesis of risk context")
    pathophysiological_rationale: str = Field(..., description="Mechanistic explanation of risk trajectory")
    evidence_based_interventions: List[str] = Field(..., description="Guideline-directed interventions")
    citations: List[EvidenceCitation] = Field(default_factory=list)
    generation_model: str
    safety_disclaimer: str = Field(
        default="AI-generated clinical synthesis for decision support only. Not an autonomous medical diagnosis. Requires review and verification by a licensed healthcare provider."
    )
    generated_at: datetime
