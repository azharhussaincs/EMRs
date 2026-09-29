from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from app.clinical.estimators.diabetes import DiabetesRiskEstimator
from app.clinical.estimators.ascvd import ASCVDRiskEstimator
from app.core.config import ClinicalDomain
from app.schemas.features import ClinicalDomainFeatures
from app.schemas.risk import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    RiskAssessmentResult,
)
from app.services.emr_ingestion import emr_ingestion_service


class BaseRiskAssessmentEngine(ABC):
    """
    Abstract interface for disease-specific clinical risk prediction engines.
    Allows swappable implementations across Diabetes, CVD, CKD, and Cancer.
    """

    @abstractmethod
    def supported_domains(self) -> List[ClinicalDomain]:
        """Return list of clinical domains this engine is currently active for."""
        pass

    @abstractmethod
    def assess_features(
        self, features: ClinicalDomainFeatures, domain: ClinicalDomain
    ) -> RiskAssessmentResult:
        """Assess disease risk stratification from pre-extracted clinical domain features."""
        pass

    @abstractmethod
    def assess_patient_risk(
        self, patient_id: str, domain: ClinicalDomain
    ) -> RiskAssessmentResult:
        """Assess disease risk stratification for an ingested patient in repository."""
        pass

    @abstractmethod
    def get_model_card(self, domain: ClinicalDomain) -> Dict[str, Any]:
        """Return model governance card including cohort assumptions and validation metrics."""
        pass

    @abstractmethod
    async def predict_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        """Legacy placeholder for future calibrated ML prediction endpoints."""
        pass


class RiskAssessmentEngine(BaseRiskAssessmentEngine):
    """
    Production-grade risk assessment engine orchestrating modular disease-specific estimators.
    Cleanly decoupled from EMR ingestion and clinical feature derivation.
    """

    def __init__(self):
        # Active pathways: Diabetes & Cardiovascular (ASCVD). CKD/Cancer scheduled for subsequent steps.
        self._active_domains: List[ClinicalDomain] = [
            ClinicalDomain.DIABETES,
            ClinicalDomain.CARDIOVASCULAR,
        ]

    def supported_domains(self) -> List[ClinicalDomain]:
        return self._active_domains

    def assess_features(
        self, features: ClinicalDomainFeatures, domain: ClinicalDomain
    ) -> RiskAssessmentResult:
        if domain == ClinicalDomain.DIABETES:
            return DiabetesRiskEstimator.evaluate(features)
        if domain == ClinicalDomain.CARDIOVASCULAR:
            return ASCVDRiskEstimator.evaluate(features)
        raise ValueError(
            f"Risk pathway for clinical domain '{domain.value}' is not active yet. "
            f"Currently active domains: {[d.value for d in self._active_domains]}"
        )

    def assess_patient_risk(
        self, patient_id: str, domain: ClinicalDomain
    ) -> RiskAssessmentResult:
        record = emr_ingestion_service.get_patient_record(patient_id)
        if not record:
            raise ValueError(
                f"Patient with identifier '{patient_id}' not found in clinical repository."
            )

        features = emr_ingestion_service.extract_features_from_record(
            record, domain_name=domain.value
        )
        return self.assess_features(features, domain=domain)

    def get_model_card(self, domain: ClinicalDomain) -> Dict[str, Any]:
        if domain == ClinicalDomain.DIABETES:
            return {
                "estimator_id": DiabetesRiskEstimator.ESTIMATOR_ID,
                "version": DiabetesRiskEstimator.ESTIMATOR_VERSION,
                "domain": "diabetes",
                "target": "Glycemic Trajectory Stratification",
                "input_features": ["hba1c_latest", "hba1c_previous", "hba1c_change", "hba1c_annualized_rate"],
                "calibration_status": "not_calibrated",
                "assumptions": "Requires >= 2 distinct historical HbA1c observations separated by time.",
                "disclaimer": "Research and engineering component only. Not validated for autonomous diagnostic decisions.",
            }
        if domain == ClinicalDomain.CARDIOVASCULAR:
            return {
                "estimator_id": ASCVDRiskEstimator.ESTIMATOR_ID,
                "version": ASCVDRiskEstimator.ESTIMATOR_VERSION,
                "domain": "cardiovascular",
                "target": "10-Year Atherosclerotic Cardiovascular Disease (ASCVD) Risk Assessment",
                "input_features": [
                    "age",
                    "gender",
                    "systolic_bp",
                    "total_cholesterol",
                    "hdl_cholesterol",
                    "smoking_status",
                    "diabetes_status",
                ],
                "calibration_status": "not_calibrated",
                "assumptions": "Requires baseline lipid panel, systolic BP, age, sex, and verified smoking/diabetes status. Uncalibrated foundation phase.",
                "disclaimer": "Research and engineering component only. Strictly non-prescriptive and non-diagnostic. Statin therapy and medication directives are withheld.",
            }
        return {
            "domain": domain.value,
            "status": "planned_for_future_phase",
        }

    async def predict_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        raise NotImplementedError("Legacy predict_risk endpoint is deprecated in favor of assess_patient_risk.")


risk_assessment_engine = RiskAssessmentEngine()
