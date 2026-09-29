import uuid
from datetime import datetime, timezone
from typing import Optional, List

from app.core.config import ClinicalDomain
from app.schemas.features import ClinicalDomainFeatures
from app.schemas.risk import RiskAssessmentResult, CalibrationStatus
from app.schemas.explanation import (
    AIExplanationContext,
    ASCVDExplanationContext,
    ExplanationBiomarkerFact,
    ExplanationTrajectorySummary,
)


def build_diabetes_explanation_context(
    assessment: RiskAssessmentResult,
    features: ClinicalDomainFeatures,
    context_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> AIExplanationContext:
    """
    Pure, deterministic function converting RiskAssessmentResult and ClinicalDomainFeatures
    into a strictly factual AIExplanationContext for downstream decision support.

    CRITICAL SAFETY PROPERTIES:
    1. Immutability: Pure function; zero mutations of input assessment or feature objects.
    2. Factual Integrity: Emits ONLY verified EMR measurements and mathematically derived metrics.
    3. Non-Diagnostic: Prohibits autonomous diagnostic claims (is_diagnostic_claim=False).
    4. Non-Prescriptive: Strictly prohibits treatment or drug directives (treatment_recommendations_allowed=False).
    5. Statistical Safety: Calibrated risk score remains strictly None if uncalibrated.
    6. Auditability: Retains source context_id, assessment_id, patient_id, timestamps, and estimator versions.
    """
    gen_time = now or datetime.now(timezone.utc)
    cid = context_id or f"ctx-dm-{uuid.uuid4().hex[:12]}"
    hba1c = features.hba1c

    # 1. Latest HbA1c fact
    if hba1c.available and hba1c.latest_value is not None:
        latest_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_latest",
            is_available=True,
            value=hba1c.latest_value,
            unit=hba1c.unit or "%",
            source_timestamp=hba1c.latest_timestamp,
            description="Most recent glycated hemoglobin (HbA1c) observation",
        )
    else:
        latest_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_latest",
            is_available=False,
            value=None,
            unit="%",
            source_timestamp=None,
            description="Most recent glycated hemoglobin (HbA1c) observation (unavailable)",
        )

    # 2. Previous HbA1c fact
    if hba1c.available and hba1c.previous_value is not None:
        prev_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_previous",
            is_available=True,
            value=hba1c.previous_value,
            unit=hba1c.unit or "%",
            source_timestamp=hba1c.previous_timestamp,
            description="Preceding glycated hemoglobin (HbA1c) baseline measurement",
        )
    else:
        prev_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_previous",
            is_available=False,
            value=None,
            unit="%",
            source_timestamp=None,
            description="Preceding glycated hemoglobin (HbA1c) baseline measurement (unavailable)",
        )

    # 3. Absolute HbA1c change fact
    if hba1c.available and hba1c.absolute_change is not None:
        change_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_change",
            is_available=True,
            value=hba1c.absolute_change,
            unit=hba1c.unit or "%",
            source_timestamp=None,
            description="Absolute difference between consecutive HbA1c observations",
        )
    else:
        change_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_change",
            is_available=False,
            value=None,
            unit="%",
            source_timestamp=None,
            description="Absolute difference between consecutive HbA1c observations (requires >= 2 observations)",
        )

    # 4. Annualized HbA1c rate fact
    if hba1c.available and hba1c.annualized_rate_of_change is not None:
        rate_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_annualized_rate",
            is_available=True,
            value=hba1c.annualized_rate_of_change,
            unit="%/year",
            source_timestamp=None,
            description="Annualized rate of HbA1c change across temporal interval",
        )
    else:
        rate_fact = ExplanationBiomarkerFact(
            feature_name="hba1c_annualized_rate",
            is_available=False,
            value=None,
            unit="%/year",
            source_timestamp=None,
            description="Annualized rate of HbA1c change (requires distinct longitudinal timestamps)",
        )

    # 5. Trajectory direction categorization
    if not hba1c.available or hba1c.measurement_count == 0:
        trajectory_direction = "unavailable"
    elif hba1c.measurement_count == 1:
        trajectory_direction = "insufficient_history"
    elif hba1c.time_interval_days == 0.0 or hba1c.status == "identical_timestamps":
        trajectory_direction = "identical_timestamps"
    elif hba1c.absolute_change is not None:
        if hba1c.absolute_change > 0.05:
            trajectory_direction = "increasing"
        elif hba1c.absolute_change < -0.05:
            trajectory_direction = "decreasing"
        else:
            trajectory_direction = "stable"
    else:
        trajectory_direction = "insufficient_history"

    trajectory_summary = ExplanationTrajectorySummary(
        measurement_count=hba1c.measurement_count,
        latest_timestamp=hba1c.latest_timestamp,
        previous_timestamp=hba1c.previous_timestamp,
        time_interval_days=hba1c.time_interval_days,
        trajectory_direction=trajectory_direction,
        annualized_rate=hba1c.annualized_rate_of_change,
        annualized_rate_unit="%/year",
    )

    # 6. Statistical calibration check (strictly withhold probability if not calibrated)
    is_calibrated = (
        assessment.calibration_status == CalibrationStatus.CALIBRATED
        and assessment.risk_estimate is not None
    )
    calibrated_score = assessment.risk_estimate if is_calibrated else None

    return AIExplanationContext(
        context_id=cid,
        patient_id=assessment.patient_id,
        assessment_id=assessment.assessment_id,
        domain=ClinicalDomain.DIABETES,
        context_generated_at=gen_time,
        assessment_timestamp=assessment.assessed_at,
        estimator_id=assessment.estimator_id,
        estimator_version=assessment.estimator_version,
        data_sufficiency=assessment.data_sufficiency,
        calibration_status=assessment.calibration_status,
        calibrated_risk_score=calibrated_score,
        is_statistically_calibrated=is_calibrated,
        latest_hba1c=latest_fact,
        previous_hba1c=prev_fact,
        absolute_change=change_fact,
        annualized_rate=rate_fact,
        trajectory_summary=trajectory_summary,
        source_features_used=list(assessment.features_used.keys()),
        unavailable_inputs=list(assessment.unavailable_inputs),
        documented_limitations=list(assessment.limitations),
        is_diagnostic_claim=False,
        treatment_recommendations_allowed=False,
        non_diagnostic_disclaimer=(
            f"{assessment.disclaimer} "
            "Factual clinical explanation context for decision support only. "
            "Strictly non-diagnostic and non-prescriptive. Treatment directives prohibited."
        ),
    )


def build_ascvd_explanation_context(
    assessment: RiskAssessmentResult,
    features: ClinicalDomainFeatures,
    context_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> ASCVDExplanationContext:
    """
    Pure, deterministic function converting RiskAssessmentResult and ClinicalDomainFeatures
    into a strictly factual ASCVDExplanationContext for downstream decision support.

    CRITICAL SAFETY PROPERTIES:
    1. Immutability: Pure function; zero mutations of input assessment or feature objects.
    2. Factual Integrity: Emits ONLY verified EMR measurements and mathematically derived metrics.
    3. Non-Diagnostic: Prohibits autonomous diagnostic claims (is_diagnostic_claim=False).
    4. Non-Prescriptive: Strictly prohibits treatment or drug directives, including statins (treatment_recommendations_allowed=False).
    5. Statistical Safety: Calibrated risk score remains strictly None if uncalibrated.
    6. Auditability: Retains source context_id, assessment_id, patient_id, timestamps, and estimator versions.
    """
    gen_time = now or datetime.now(timezone.utc)
    cid = context_id or f"ctx-cvd-{uuid.uuid4().hex[:12]}"
    ascvd = features.ascvd

    # Safe handling if ascvd features are completely absent
    if not ascvd:
        sbp_fact = ExplanationBiomarkerFact(
            feature_name="systolic_bp",
            is_available=False,
            value=None,
            unit="mmHg",
            source_timestamp=None,
            description="Latest resting systolic blood pressure (unavailable)",
        )
        tc_fact = ExplanationBiomarkerFact(
            feature_name="total_cholesterol",
            is_available=False,
            value=None,
            unit="mg/dL",
            source_timestamp=None,
            description="Latest total serum cholesterol (unavailable)",
        )
        hdl_fact = ExplanationBiomarkerFact(
            feature_name="hdl_cholesterol",
            is_available=False,
            value=None,
            unit="mg/dL",
            source_timestamp=None,
            description="Latest high-density lipoprotein cholesterol (unavailable)",
        )

        return ASCVDExplanationContext(
            context_id=cid,
            patient_id=assessment.patient_id,
            assessment_id=assessment.assessment_id,
            domain=ClinicalDomain.CARDIOVASCULAR,
            context_generated_at=gen_time,
            assessment_timestamp=assessment.assessed_at,
            estimator_id=assessment.estimator_id,
            estimator_version=assessment.estimator_version,
            data_sufficiency=assessment.data_sufficiency,
            calibration_status=assessment.calibration_status,
            calibrated_risk_score=None,
            is_statistically_calibrated=False,
            age_years=None,
            age_available=False,
            gender=None,
            gender_available=False,
            systolic_bp=sbp_fact,
            systolic_bp_mean=None,
            systolic_bp_std=None,
            systolic_bp_count=0,
            total_cholesterol=tc_fact,
            hdl_cholesterol=hdl_fact,
            smoking_status=None,
            smoking_status_available=False,
            smoking_status_code=None,
            has_diabetes=None,
            diabetes_status_available=False,
            diabetes_source_evidence=[],
            source_features_used=[],
            unavailable_inputs=list(assessment.unavailable_inputs),
            documented_limitations=list(assessment.limitations),
            is_diagnostic_claim=False,
            treatment_recommendations_allowed=False,
            non_diagnostic_disclaimer=(
                f"{assessment.disclaimer} "
                "Factual clinical explanation context for decision support only. "
                "Strictly non-diagnostic and non-prescriptive. Treatment directives and statin therapy recommendations prohibited."
            ),
        )

    # 1. Blood pressure fact
    sbp = ascvd.systolic_bp
    if sbp.available and sbp.latest_value is not None:
        sbp_fact = ExplanationBiomarkerFact(
            feature_name="systolic_bp",
            is_available=True,
            value=sbp.latest_value,
            unit=sbp.unit or "mmHg",
            source_timestamp=sbp.latest_timestamp,
            description="Latest resting systolic blood pressure",
        )
    else:
        sbp_fact = ExplanationBiomarkerFact(
            feature_name="systolic_bp",
            is_available=False,
            value=None,
            unit="mmHg",
            source_timestamp=None,
            description="Latest resting systolic blood pressure (unavailable)",
        )

    # 2. Total cholesterol fact
    tc = ascvd.total_cholesterol
    if tc.available and tc.latest_value is not None:
        tc_fact = ExplanationBiomarkerFact(
            feature_name="total_cholesterol",
            is_available=True,
            value=tc.latest_value,
            unit=tc.unit or "mg/dL",
            source_timestamp=tc.latest_timestamp,
            description="Latest total serum cholesterol",
        )
    else:
        tc_fact = ExplanationBiomarkerFact(
            feature_name="total_cholesterol",
            is_available=False,
            value=None,
            unit="mg/dL",
            source_timestamp=None,
            description="Latest total serum cholesterol (unavailable)",
        )

    # 3. HDL cholesterol fact
    hdl = ascvd.hdl_cholesterol
    if hdl.available and hdl.latest_value is not None:
        hdl_fact = ExplanationBiomarkerFact(
            feature_name="hdl_cholesterol",
            is_available=True,
            value=hdl.latest_value,
            unit=hdl.unit or "mg/dL",
            source_timestamp=hdl.latest_timestamp,
            description="Latest high-density lipoprotein (HDL) cholesterol",
        )
    else:
        hdl_fact = ExplanationBiomarkerFact(
            feature_name="hdl_cholesterol",
            is_available=False,
            value=None,
            unit="mg/dL",
            source_timestamp=None,
            description="Latest high-density lipoprotein (HDL) cholesterol (unavailable)",
        )

    # 4. Statistical calibration check (strictly withhold probability if not calibrated)
    is_calibrated = (
        assessment.calibration_status == CalibrationStatus.CALIBRATED
        and assessment.risk_estimate is not None
    )
    calibrated_score = assessment.risk_estimate if is_calibrated else None

    return ASCVDExplanationContext(
        context_id=cid,
        patient_id=assessment.patient_id,
        assessment_id=assessment.assessment_id,
        domain=ClinicalDomain.CARDIOVASCULAR,
        context_generated_at=gen_time,
        assessment_timestamp=assessment.assessed_at,
        estimator_id=assessment.estimator_id,
        estimator_version=assessment.estimator_version,
        data_sufficiency=assessment.data_sufficiency,
        calibration_status=assessment.calibration_status,
        calibrated_risk_score=calibrated_score,
        is_statistically_calibrated=is_calibrated,
        age_years=ascvd.age_years,
        age_available=ascvd.age_available,
        gender=ascvd.gender,
        gender_available=ascvd.gender_available,
        systolic_bp=sbp_fact,
        systolic_bp_mean=sbp.mean,
        systolic_bp_std=sbp.standard_deviation,
        systolic_bp_count=sbp.measurement_count,
        total_cholesterol=tc_fact,
        hdl_cholesterol=hdl_fact,
        smoking_status=ascvd.smoking_status.value if ascvd.smoking_status.available else None,
        smoking_status_available=ascvd.smoking_status.available,
        smoking_status_code=ascvd.smoking_status.source_code,
        has_diabetes=ascvd.diabetes_history.has_diabetes if ascvd.diabetes_history.available else None,
        diabetes_status_available=ascvd.diabetes_history.available,
        diabetes_source_evidence=list(ascvd.diabetes_history.source_evidence),
        source_features_used=list(assessment.features_used.keys()),
        unavailable_inputs=list(assessment.unavailable_inputs),
        documented_limitations=list(assessment.limitations),
        is_diagnostic_claim=False,
        treatment_recommendations_allowed=False,
        non_diagnostic_disclaimer=(
            f"{assessment.disclaimer} "
            "Factual clinical explanation context for decision support only. "
            "Strictly non-diagnostic and non-prescriptive. Treatment directives and statin therapy recommendations prohibited."
        ),
    )

