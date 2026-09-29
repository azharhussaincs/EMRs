from typing import Optional
from app.core.config import ClinicalDomain
from app.schemas.features import ClinicalDomainFeatures
from app.schemas.risk import RiskAssessmentResult
from app.schemas.explanation import AIExplanationContext, ASCVDExplanationContext
from app.clinical.explanation import (
    build_diabetes_explanation_context,
    build_ascvd_explanation_context,
)
from app.services.emr_ingestion import emr_ingestion_service
from app.services.risk_engine import risk_assessment_engine


class ExplanationContextService:
    """
    Service coordinating the deterministic extraction of AI Explanation Contexts
    from validated EMR records and risk assessments.
    Strictly factual, non-generative, and non-prescriptive.
    """

    def get_diabetes_context_for_patient(
        self, patient_id: str
    ) -> AIExplanationContext:
        """
        Retrieves ingested patient record, computes longitudinal trajectory features,
        evaluates risk assessment, and produces a strictly factual AIExplanationContext.
        """
        record = emr_ingestion_service.get_patient_record(patient_id)
        if not record:
            raise ValueError(
                f"Patient with identifier '{patient_id}' not found in clinical repository."
            )

        features = emr_ingestion_service.extract_features_from_record(
            record, domain_name="diabetes"
        )
        assessment = risk_assessment_engine.assess_features(
            features, domain=ClinicalDomain.DIABETES
        )

        return build_diabetes_explanation_context(
            assessment=assessment, features=features
        )

    def prepare_diabetes_context_direct(
        self,
        features: ClinicalDomainFeatures,
        assessment: RiskAssessmentResult,
    ) -> AIExplanationContext:
        """
        Direct pure functional adapter for external features and assessments.
        """
        return build_diabetes_explanation_context(
            assessment=assessment, features=features
        )

    def get_cardiovascular_context_for_patient(
        self, patient_id: str
    ) -> ASCVDExplanationContext:
        """
        Retrieves ingested patient record, computes ASCVD clinical risk factor features,
        evaluates risk assessment, and produces a strictly factual ASCVDExplanationContext.
        """
        record = emr_ingestion_service.get_patient_record(patient_id)
        if not record:
            raise ValueError(
                f"Patient with identifier '{patient_id}' not found in clinical repository."
            )

        features = emr_ingestion_service.extract_features_from_record(
            record, domain_name="cardiovascular"
        )
        assessment = risk_assessment_engine.assess_features(
            features, domain=ClinicalDomain.CARDIOVASCULAR
        )

        return build_ascvd_explanation_context(
            assessment=assessment, features=features
        )

    def prepare_cardiovascular_context_direct(
        self,
        features: ClinicalDomainFeatures,
        assessment: RiskAssessmentResult,
    ) -> ASCVDExplanationContext:
        """
        Direct pure functional adapter for external cardiovascular features and assessments.
        """
        return build_ascvd_explanation_context(
            assessment=assessment, features=features
        )


explanation_service = ExplanationContextService()

