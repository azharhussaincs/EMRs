from abc import ABC, abstractmethod
from typing import Dict, Any
from app.schemas.genai import ClinicalNarrativeRequest, ClinicalNarrativeResponse
from app.schemas.risk import RiskAssessmentResponse


class BaseClinicalNarrativeGenerator(ABC):
    """
    Abstract interface for Generative AI Clinical Narrative Synthesizers.
    Decoupled from specific LLM providers (Gemini, Bedrock, OpenAI, local vLLM).
    Enforces clinical guideline grounding, safety disclaimers, and audience tailoring.
    """

    @abstractmethod
    async def synthesize_rationale(
        self,
        request: ClinicalNarrativeRequest,
        assessment_context: RiskAssessmentResponse,
    ) -> ClinicalNarrativeResponse:
        """Synthesize clinical rationale grounded in consensus medical guidelines."""
        pass

    @abstractmethod
    def get_prompt_template_version(self) -> str:
        """Return versioned prompt identifier for audit reproducibility."""
        pass
