import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.config import ClinicalDomain
from app.schemas.features import ClinicalDomainFeatures
from app.schemas.risk import (
    RiskAssessmentResult,
    DataSufficiencyStatus,
    CalibrationStatus,
    UsedFeatureValue,
)


class DiabetesRiskEstimator:
    """
    Initial diabetes risk pathway based strictly on validated, longitudinal HbA1c trajectory.
    Adheres to strict statistical safety:
    - Does not fabricate probabilities.
    - Does not label disease status.
    - Returns 'not_calibrated' until statistical cohort calibration is complete.
    - Does not mutate input features.
    """

    ESTIMATOR_ID = "diabetes_hba1c_trajectory_v0_1"
    ESTIMATOR_VERSION = "0.1.0-foundation"

    @classmethod
    def evaluate(cls, features: ClinicalDomainFeatures) -> RiskAssessmentResult:
        """
        Evaluates diabetes trajectory status from ClinicalDomainFeatures.
        Pure function: does not mutate inputs.
        """
        assessment_id = f"assess-dm-{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc)
        hba1c = features.hba1c

        # Case 1: HbA1c feature is unavailable / zero measurements
        if not hba1c.available or hba1c.measurement_count == 0:
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                patient_id=features.patient_id,
                assessed_at=now_utc,
                domain=ClinicalDomain.DIABETES,
                estimator_id=cls.ESTIMATOR_ID,
                estimator_version=cls.ESTIMATOR_VERSION,
                data_sufficiency=DataSufficiencyStatus.UNAVAILABLE,
                calibration_status=CalibrationStatus.INSUFFICIENT_MODEL,
                risk_estimate=None,
                confidence_interval=None,
                features_used={},
                unavailable_inputs=[
                    "hba1c_latest",
                    "hba1c_previous",
                    "hba1c_change",
                    "hba1c_annualized_rate",
                ],
                limitations=[
                    "No HbA1c observations found in patient EMR.",
                    "Glycemic trajectory stratification cannot be evaluated without baseline lab measurements.",
                ],
            )

        # Case 2: Single measurement only
        if hba1c.measurement_count == 1:
            features_used = {
                "hba1c_latest": UsedFeatureValue(
                    feature_name="hba1c_latest",
                    value=hba1c.latest_value,
                    unit=hba1c.unit,
                    source_timestamp=hba1c.latest_timestamp,
                    description="Most recent glycated hemoglobin measurement",
                )
            }
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                patient_id=features.patient_id,
                assessed_at=now_utc,
                domain=ClinicalDomain.DIABETES,
                estimator_id=cls.ESTIMATOR_ID,
                estimator_version=cls.ESTIMATOR_VERSION,
                data_sufficiency=DataSufficiencyStatus.INSUFFICIENT,
                calibration_status=CalibrationStatus.NOT_CALIBRATED,
                risk_estimate=None,
                confidence_interval=None,
                features_used=features_used,
                unavailable_inputs=[
                    "hba1c_previous",
                    "hba1c_change",
                    "hba1c_annualized_rate",
                ],
                limitations=[
                    "Only 1 HbA1c observation is present in the record.",
                    "Longitudinal trajectory assessment requires at least 2 distinct historical measurements.",
                    "Rate of change cannot be derived from an isolated static measurement.",
                ],
            )

        # Case 3: Identical timestamps (time delta is zero)
        if hba1c.status == "identical_timestamps" or (hba1c.time_interval_days is not None and hba1c.time_interval_days == 0.0):
            features_used = {
                "hba1c_latest": UsedFeatureValue(
                    feature_name="hba1c_latest",
                    value=hba1c.latest_value,
                    unit=hba1c.unit,
                    source_timestamp=hba1c.latest_timestamp,
                    description="Most recent glycated hemoglobin measurement",
                ),
                "hba1c_previous": UsedFeatureValue(
                    feature_name="hba1c_previous",
                    value=hba1c.previous_value,
                    unit=hba1c.unit,
                    source_timestamp=hba1c.previous_timestamp,
                    description="Preceding glycated hemoglobin measurement",
                ),
                "hba1c_change": UsedFeatureValue(
                    feature_name="hba1c_change",
                    value=hba1c.absolute_change,
                    unit=hba1c.unit,
                    description="Absolute difference between consecutive measurements",
                ),
            }
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                patient_id=features.patient_id,
                assessed_at=now_utc,
                domain=ClinicalDomain.DIABETES,
                estimator_id=cls.ESTIMATOR_ID,
                estimator_version=cls.ESTIMATOR_VERSION,
                data_sufficiency=DataSufficiencyStatus.INSUFFICIENT,
                calibration_status=CalibrationStatus.NOT_CALIBRATED,
                risk_estimate=None,
                confidence_interval=None,
                features_used=features_used,
                unavailable_inputs=["hba1c_annualized_rate"],
                limitations=[
                    "Consecutive HbA1c observations share identical timestamps (time interval is 0 days).",
                    "Annualized rate of change cannot be derived without distinct temporal separation.",
                ],
            )

        # Case 4: Sufficient longitudinal data (n >= 2 with distinct timestamps)
        features_used = {
            "hba1c_latest": UsedFeatureValue(
                feature_name="hba1c_latest",
                value=hba1c.latest_value,
                unit=hba1c.unit,
                source_timestamp=hba1c.latest_timestamp,
                description="Most recent glycated hemoglobin measurement",
            ),
            "hba1c_previous": UsedFeatureValue(
                feature_name="hba1c_previous",
                value=hba1c.previous_value,
                unit=hba1c.unit,
                source_timestamp=hba1c.previous_timestamp,
                description="Preceding glycated hemoglobin measurement",
            ),
            "hba1c_change": UsedFeatureValue(
                feature_name="hba1c_change",
                value=hba1c.absolute_change,
                unit=hba1c.unit,
                description="Absolute difference between consecutive measurements",
            ),
            "hba1c_annualized_rate": UsedFeatureValue(
                feature_name="hba1c_annualized_rate",
                value=hba1c.annualized_rate_of_change,
                unit="%/year",
                description="Annualized rate of change derived across temporal interval",
            ),
        }

        return RiskAssessmentResult(
            assessment_id=assessment_id,
            patient_id=features.patient_id,
            assessed_at=now_utc,
            domain=ClinicalDomain.DIABETES,
            estimator_id=cls.ESTIMATOR_ID,
            estimator_version=cls.ESTIMATOR_VERSION,
            data_sufficiency=DataSufficiencyStatus.SUFFICIENT,
            calibration_status=CalibrationStatus.NOT_CALIBRATED,
            risk_estimate=None,  # Explicitly uncalibrated: no fabricated numbers
            confidence_interval=None,
            features_used=features_used,
            unavailable_inputs=[],
            limitations=[
                "Estimator is in research foundation phase (v0.1.0-foundation).",
                "Empirical population cohort calibration is required before statistical risk probabilities can be emitted.",
                "Trajectory features reflect longitudinal progression; arbitrary heuristics are rejected.",
                "Does not constitute a clinical diagnosis or treatment directive.",
            ],
        )
