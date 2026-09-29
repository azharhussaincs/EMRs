from datetime import datetime
from pydantic import BaseModel, Field
from app.core.config import ClinicalDomain


class LLMStructuredNarrativePayload(BaseModel):
    """
    Direct structured JSON contract expected from the LLM provider.
    Strictly prohibits unvalidated free-form markdown or conversational chatter.
    """
    summary: str = Field(
        ...,
        description="Factual clinical synthesis of the patient's glycemic trajectory",
    )
    observed_trajectory: str = Field(
        ...,
        description="Chronological description of observed HbA1c values, baseline change, and annualized rate",
    )
    data_limitations: str = Field(
        ...,
        description="Explicit documentation of data sufficiency, measurement count, and unavailable features",
    )
    statistical_calibration_status: str = Field(
        ...,
        description="Explicit confirmation of uncalibrated status and withholding of numerical probability",
    )
    disclaimer: str = Field(
        ...,
        description="Mandatory non-diagnostic and non-prescriptive regulatory decision boundary disclaimer",
    )


class ClinicalNarrativeExplanation(BaseModel):
    """
    Complete, validated clinical explanation narrative returned to clinician portal.
    Combines validated LLM generation with immutable audit and context traceability fields.
    """
    narrative_id: str = Field(..., description="Unique narrative generation execution identifier")
    context_id: str = Field(..., description="Reference to underlying AIExplanationContext")
    patient_id: str = Field(..., description="Pseudonymous patient identifier")
    assessment_id: str = Field(..., description="Reference to source RiskAssessmentResult")
    domain: ClinicalDomain = Field(..., description="Target disease domain (diabetes)")
    summary: str
    observed_trajectory: str
    data_limitations: str
    statistical_calibration_status: str
    disclaimer: str
    provider: str = Field(..., description="LLM provider used (e.g. mock, gemini, openai)")
    model_name: str = Field(..., description="Underlying model identifier")
    generated_at: datetime = Field(..., description="UTC timestamp of narrative synthesis")
