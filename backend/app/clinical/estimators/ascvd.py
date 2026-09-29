import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.config import ClinicalDomain
from app.schemas.features import ClinicalDomainFeatures, ASCVDClinicalFeatures
from app.schemas.risk import (
    RiskAssessmentResult,
    DataSufficiencyStatus,
    CalibrationStatus,
    UsedFeatureValue,
)


class ASCVDRiskEstimator:
    """
    Cardiovascular Disease / ASCVD risk pathway foundation.
    Evaluates clinical risk factor sufficiency and trajectory features.

    Adheres to strict clinical AI safety standards:
    - Does NOT fabricate an ASCVD percentage or probability.
    - risk_estimate is strictly None until formal calibrated cohort models are integrated.
    - calibration_status is strictly NOT_CALIBRATED or INSUFFICIENT_MODEL.
    - Does NOT impute missing features (smoking, diabetes, lipids, BP).
    - Pure function: does not mutate input features.
    """

    ESTIMATOR_ID = "ascvd_pooled_cohort_v0_1"
    ESTIMATOR_VERSION = "0.1.0-foundation"

    @classmethod
    def evaluate(cls, features: ClinicalDomainFeatures) -> RiskAssessmentResult:
        """
        Evaluates ASCVD feature sufficiency and baseline status.
        Pure function: does not mutate inputs.
        """
        assessment_id = f"assess-cvd-{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc)
        ascvd = features.ascvd

        # Case 1: ASCVD feature model completely missing or both primary clinical markers unavailable
        if not ascvd or (not ascvd.systolic_bp.available and not ascvd.total_cholesterol.available):
            missing_all = [
                "age",
                "gender",
                "systolic_bp",
                "total_cholesterol",
                "hdl_cholesterol",
                "smoking_status",
                "diabetes_status",
            ]
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                patient_id=features.patient_id,
                assessed_at=now_utc,
                domain=ClinicalDomain.CARDIOVASCULAR,
                estimator_id=cls.ESTIMATOR_ID,
                estimator_version=cls.ESTIMATOR_VERSION,
                data_sufficiency=DataSufficiencyStatus.UNAVAILABLE,
                calibration_status=CalibrationStatus.INSUFFICIENT_MODEL,
                risk_estimate=None,
                confidence_interval=None,
                features_used={},
                unavailable_inputs=missing_all,
                limitations=[
                    "No cardiovascular or lipid observations found in patient EMR.",
                    "ASCVD risk assessment requires baseline blood pressure and lipid panel measurements.",
                ],
                disclaimer="Cardiovascular / ASCVD risk assessment foundation. Strictly non-prescriptive and non-diagnostic.",
            )

        # Build dictionary of used features
        features_used: Dict[str, UsedFeatureValue] = {}

        if ascvd.age_available and ascvd.age_years is not None:
            features_used["age"] = UsedFeatureValue(
                feature_name="age",
                value=float(ascvd.age_years),
                unit="years",
                description="Chronological age derived from birth date",
            )

        if ascvd.gender_available and ascvd.gender:
            features_used["gender"] = UsedFeatureValue(
                feature_name="gender",
                unit=None,
                description=f"Administrative sex: {ascvd.gender}",
            )

        if ascvd.systolic_bp.available and ascvd.systolic_bp.latest_value is not None:
            features_used["systolic_bp"] = UsedFeatureValue(
                feature_name="systolic_bp",
                value=ascvd.systolic_bp.latest_value,
                unit=ascvd.systolic_bp.unit,
                source_timestamp=ascvd.systolic_bp.latest_timestamp,
                description="Latest resting systolic blood pressure",
            )

        if ascvd.total_cholesterol.available and ascvd.total_cholesterol.latest_value is not None:
            features_used["total_cholesterol"] = UsedFeatureValue(
                feature_name="total_cholesterol",
                value=ascvd.total_cholesterol.latest_value,
                unit=ascvd.total_cholesterol.unit,
                source_timestamp=ascvd.total_cholesterol.latest_timestamp,
                description="Latest total serum cholesterol",
            )

        if ascvd.hdl_cholesterol.available and ascvd.hdl_cholesterol.latest_value is not None:
            features_used["hdl_cholesterol"] = UsedFeatureValue(
                feature_name="hdl_cholesterol",
                value=ascvd.hdl_cholesterol.latest_value,
                unit=ascvd.hdl_cholesterol.unit,
                source_timestamp=ascvd.hdl_cholesterol.latest_timestamp,
                description="Latest high-density lipoprotein (HDL) cholesterol",
            )

        if ascvd.smoking_status.available and ascvd.smoking_status.value:
            features_used["smoking_status"] = UsedFeatureValue(
                feature_name="smoking_status",
                unit=None,
                source_timestamp=None,
                description=f"Smoking status: {ascvd.smoking_status.value} ({ascvd.smoking_status.source_code or 'documented'})",
            )

        if ascvd.diabetes_history.available and ascvd.diabetes_history.has_diabetes is not None:
            diag_desc = (
                "Diabetes mellitus confirmed present"
                if ascvd.diabetes_history.has_diabetes
                else "Diabetes mellitus absent or not documented"
            )
            features_used["diabetes_status"] = UsedFeatureValue(
                feature_name="diabetes_status",
                unit=None,
                description=diag_desc,
            )

        # Case 2: Partial data sufficiency (some required inputs missing)
        if not ascvd.is_sufficient_for_ascvd:
            missing_descriptions = [
                f"Missing required clinical parameter: '{f}'" for f in ascvd.missing_required_features
            ]
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                patient_id=features.patient_id,
                assessed_at=now_utc,
                domain=ClinicalDomain.CARDIOVASCULAR,
                estimator_id=cls.ESTIMATOR_ID,
                estimator_version=cls.ESTIMATOR_VERSION,
                data_sufficiency=DataSufficiencyStatus.INSUFFICIENT,
                calibration_status=CalibrationStatus.NOT_CALIBRATED,
                risk_estimate=None,  # Withheld: never emit heuristic percentage
                confidence_interval=None,
                features_used=features_used,
                unavailable_inputs=ascvd.missing_required_features,
                limitations=[
                    f"Incomplete ASCVD risk factor profile ({len(ascvd.missing_required_features)} required inputs missing).",
                    *missing_descriptions,
                    "Missing values are explicitly preserved without statistical imputation or heuristic assumptions.",
                    "Estimator does not emit fabricated numerical probabilities.",
                ],
                disclaimer="Cardiovascular / ASCVD risk assessment foundation. Strictly non-prescriptive and non-diagnostic.",
            )

        # Case 3: Complete data sufficiency (all 7 required parameters present)
        return RiskAssessmentResult(
            assessment_id=assessment_id,
            patient_id=features.patient_id,
            assessed_at=now_utc,
            domain=ClinicalDomain.CARDIOVASCULAR,
            estimator_id=cls.ESTIMATOR_ID,
            estimator_version=cls.ESTIMATOR_VERSION,
            data_sufficiency=DataSufficiencyStatus.SUFFICIENT,
            calibration_status=CalibrationStatus.NOT_CALIBRATED,
            risk_estimate=None,  # Uncalibrated foundation phase: strictly withheld
            confidence_interval=None,
            features_used=features_used,
            unavailable_inputs=[],
            limitations=[
                "Estimator is in research foundation phase (v0.1.0-foundation).",
                "Estimator is uncalibrated against longitudinal population cohorts; empirical risk probability is strictly withheld.",
                "Empirical 10-year ASCVD risk probabilities are strictly withheld until calibrated cohort models (e.g. ACC/AHA Pooled Cohort Equations) are formally validated.",
                "Clinical features reflect verified risk factor presence; rule-of-thumb approximations are rejected.",
                "Does not constitute clinical diagnosis, statin prescription recommendation, or treatment directive.",
            ],
            disclaimer="Cardiovascular / ASCVD risk assessment foundation. Strictly non-prescriptive and non-diagnostic.",
        )
