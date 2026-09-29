import copy
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import ClinicalDomain
from app.core.audit import audit_service
from app.schemas.features import (
    ClinicalDomainFeatures,
    HbA1cTrajectoryFeature,
    EGFRTrajectoryFeature,
    SystolicBPTrajectoryFeature,
)
from app.schemas.risk import (
    RiskAssessmentResult,
    DataSufficiencyStatus,
    CalibrationStatus,
)
from app.clinical.estimators.diabetes import DiabetesRiskEstimator
from app.clinical.explanation import build_diabetes_explanation_context
from app.services.explanation_service import explanation_service


def build_mock_assessment_and_features(
    patient_id: str = "PT-EXPLAIN-TEST-01",
    hba1c_count: int = 2,
    latest_val: float = 8.2,
    prev_val: float = 7.6,
    time_interval_days: float = 253.0,
    annualized_rate: float = 0.86,
    hba1c_available: bool = True,
    status: str = "available",
):
    now = datetime.now(timezone.utc)
    if not hba1c_available or hba1c_count == 0:
        hba1c_feat = HbA1cTrajectoryFeature(
            available=False,
            status="unavailable",
            measurement_count=0,
            unit="%",
        )
    elif hba1c_count == 1:
        hba1c_feat = HbA1cTrajectoryFeature(
            available=True,
            status="single_measurement",
            measurement_count=1,
            latest_value=latest_val,
            latest_timestamp=now,
            unit="%",
        )
    else:
        hba1c_feat = HbA1cTrajectoryFeature(
            available=True,
            status=status,
            measurement_count=hba1c_count,
            latest_value=latest_val,
            latest_timestamp=now,
            previous_value=prev_val,
            previous_timestamp=now,
            absolute_change=round(latest_val - prev_val, 2),
            time_interval_days=time_interval_days,
            annualized_rate_of_change=annualized_rate if time_interval_days > 0 else None,
            unit="%",
        )

    features = ClinicalDomainFeatures(
        patient_id=patient_id,
        domain="diabetes",
        extracted_at=now,
        hba1c=hba1c_feat,
        egfr=EGFRTrajectoryFeature(available=False, status="unavailable", unit="mL/min/1.73m²"),
        systolic_bp=SystolicBPTrajectoryFeature(available=False, status="unavailable", unit="mmHg"),
        feature_vector={"hba1c_latest": latest_val} if hba1c_available else {},
    )

    assessment = DiabetesRiskEstimator.evaluate(features)
    return features, assessment


def test_1_correct_hba1c_values_copied_into_explanation_context():
    features, assessment = build_mock_assessment_and_features(
        hba1c_count=3, latest_val=8.2, prev_val=7.6, annualized_rate=0.86
    )
    context = build_diabetes_explanation_context(assessment=assessment, features=features)

    assert context.latest_hba1c.is_available is True
    assert context.latest_hba1c.value == 8.2
    assert context.latest_hba1c.unit == "%"

    assert context.previous_hba1c.is_available is True
    assert context.previous_hba1c.value == 7.6
    assert context.previous_hba1c.unit == "%"

    assert context.absolute_change.is_available is True
    assert context.absolute_change.value == 0.6
    assert context.absolute_change.unit == "%"

    assert context.annualized_rate.is_available is True
    assert context.annualized_rate.value == 0.86
    assert context.annualized_rate.unit == "%/year"


def test_2_correct_trajectory_timestamp_preservation():
    features, assessment = build_mock_assessment_and_features(
        hba1c_count=2, latest_val=8.2, prev_val=7.6, time_interval_days=253.0
    )
    context = build_diabetes_explanation_context(assessment=assessment, features=features)

    assert context.trajectory_summary.measurement_count == 2
    assert context.trajectory_summary.time_interval_days == 253.0
    assert context.trajectory_summary.latest_timestamp == features.hba1c.latest_timestamp
    assert context.trajectory_summary.previous_timestamp == features.hba1c.previous_timestamp
    assert context.trajectory_summary.trajectory_direction == "increasing"


def test_3_missing_hba1c_history_handled_safely():
    # Zero measurements
    features_zero, assessment_zero = build_mock_assessment_and_features(hba1c_available=False)
    context_zero = build_diabetes_explanation_context(assessment=assessment_zero, features=features_zero)

    assert context_zero.latest_hba1c.is_available is False
    assert context_zero.latest_hba1c.value is None
    assert context_zero.previous_hba1c.is_available is False
    assert context_zero.previous_hba1c.value is None
    assert context_zero.absolute_change.is_available is False
    assert context_zero.annualized_rate.is_available is False
    assert context_zero.trajectory_summary.trajectory_direction == "unavailable"
    assert "hba1c_latest" in context_zero.unavailable_inputs

    # Single measurement
    features_single, assessment_single = build_mock_assessment_and_features(hba1c_count=1, latest_val=7.4)
    context_single = build_diabetes_explanation_context(assessment=assessment_single, features=features_single)

    assert context_single.latest_hba1c.is_available is True
    assert context_single.latest_hba1c.value == 7.4
    assert context_single.previous_hba1c.is_available is False
    assert context_single.previous_hba1c.value is None
    assert context_single.absolute_change.is_available is False
    assert context_single.annualized_rate.is_available is False
    assert context_single.trajectory_summary.trajectory_direction == "insufficient_history"
    assert "hba1c_previous" in context_single.unavailable_inputs


def test_4_uncalibrated_risk_remains_explicitly_uncalibrated():
    features, assessment = build_mock_assessment_and_features()
    context = build_diabetes_explanation_context(assessment=assessment, features=features)

    assert context.calibration_status == CalibrationStatus.NOT_CALIBRATED
    assert context.is_statistically_calibrated is False


def test_5_no_fabricated_risk_probability_appears():
    features, assessment = build_mock_assessment_and_features()
    context = build_diabetes_explanation_context(assessment=assessment, features=features)

    # Risk score must be strictly None to prevent fabricated claims
    assert context.calibrated_risk_score is None


def test_6_no_treatment_recommendation_appears():
    features, assessment = build_mock_assessment_and_features()
    context = build_diabetes_explanation_context(assessment=assessment, features=features)

    assert context.treatment_recommendations_allowed is False
    assert context.is_diagnostic_claim is False
    assert "non-diagnostic" in context.non_diagnostic_disclaimer.lower()
    assert "non-prescriptive" in context.non_diagnostic_disclaimer.lower()


def test_7_input_objects_remain_unchanged():
    features, assessment = build_mock_assessment_and_features()
    features_copy = copy.deepcopy(features)
    assessment_copy = copy.deepcopy(assessment)

    build_diabetes_explanation_context(assessment=assessment, features=features)

    assert features == features_copy
    assert assessment == assessment_copy


def test_8_assessment_model_metadata_preserved():
    features, assessment = build_mock_assessment_and_features()
    context = build_diabetes_explanation_context(assessment=assessment, features=features)

    assert context.assessment_id == assessment.assessment_id
    assert context.patient_id == assessment.patient_id
    assert context.domain == ClinicalDomain.DIABETES
    assert context.estimator_id == "diabetes_hba1c_trajectory_v0_1"
    assert context.estimator_version == "0.1.0-foundation"
    assert context.assessment_timestamp == assessment.assessed_at
    assert len(context.source_features_used) > 0
    assert len(context.documented_limitations) > 0


@pytest.mark.asyncio
async def test_9_explanation_context_endpoint_works():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ingest standard patient
        sample_res = await ac.get("/api/v1/emr/sample-fhir")
        bundle = sample_res.json()
        ingest_res = await ac.post("/api/v1/emr/ingest", json=bundle)
        assert ingest_res.status_code == 201
        patient_id = ingest_res.json()["patient_record"]["patient_id"]

        # Call the GenAI explanation-context endpoint
        res = await ac.get(
            f"/api/v1/genai/explanation-context/patients/{patient_id}/diabetes",
            headers={"X-Actor-ID": "dr-endocrinologist-01"},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["patient_id"] == patient_id
        assert data["domain"] == "diabetes"
        assert data["latest_hba1c"]["value"] == 8.2
        assert data["previous_hba1c"]["value"] == 7.6
        assert data["absolute_change"]["value"] == 0.6
        assert data["annualized_rate"]["value"] is not None
        assert data["calibrated_risk_score"] is None
        assert data["is_statistically_calibrated"] is False
        assert data["treatment_recommendations_allowed"] is False
        assert data["is_diagnostic_claim"] is False

        # Verify convenience endpoint on /risk also works
        risk_alias_res = await ac.get(
            f"/api/v1/risk/patients/{patient_id}/diabetes/explanation-context"
        )
        assert risk_alias_res.status_code == 200
        assert risk_alias_res.json()["patient_id"] == patient_id


@pytest.mark.asyncio
async def test_10_audit_traceability_fields_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        sample_res = await ac.get("/api/v1/emr/sample-fhir")
        ingest_res = await ac.post("/api/v1/emr/ingest", json=sample_res.json())
        patient_id = ingest_res.json()["patient_record"]["patient_id"]

        res = await ac.get(
            f"/api/v1/genai/explanation-context/patients/{patient_id}/diabetes",
            headers={"X-Actor-ID": "audit-auditor-99"},
        )
        assert res.status_code == 200
        data = res.json()

        # Audit / traceability fields must be present
        assert "context_id" in data
        assert data["context_id"].startswith("ctx-dm-")
        assert "assessment_id" in data
        assert data["assessment_id"].startswith("assess-dm-")

        # Check HIPAA audit trail
        events = audit_service.get_recent_events()
        matching_events = [
            e for e in events
            if e.action == "get_diabetes_explanation_context"
            and e.resource_id == patient_id
            and e.actor_id == "audit-auditor-99"
        ]
        assert len(matching_events) >= 1
        audit_event = matching_events[-1]
        assert audit_event.metadata["context_id"] == data["context_id"]
        assert audit_event.metadata["assessment_id"] == data["assessment_id"]
