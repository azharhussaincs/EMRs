from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.core.config import ClinicalDomain
from app.schemas.risk import RiskAssessmentRequest, RiskAssessmentResponse


class BaseRiskAssessmentEngine(ABC):
    """
    Abstract interface for disease-specific clinical risk prediction engines.
    Allows swappable implementations (e.g., XGBoost, LightGBM, Deep Learning, Survival Analysis).
    """

    @abstractmethod
    def supported_domains(self) -> List[ClinicalDomain]:
        """Return list of clinical domains this engine is validated for."""
        pass

    @abstractmethod
    def get_model_card(self, domain: ClinicalDomain) -> Dict[str, Any]:
        """Return model governance card including training cohort, AUC-ROC, and validation metrics."""
        pass

    @abstractmethod
    async def predict_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        """Execute risk score computation, confidence intervals, and feature attributions."""
        pass
