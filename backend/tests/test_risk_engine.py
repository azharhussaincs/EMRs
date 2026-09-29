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
from app.services.risk_engine import risk_assessment_engine


def build_mock_features(
    patient_id: str = "test-patient-dm",
    hba1c_count: int = 2,
    latest_val: float = 8.2,
    prev_val: float = 7.6,
    time_interval_days: float = 253.0,
    annualized_rate: float = 0.86,
    hba1c_available: bool = True,
    status: str = "available",
) -> ClinicalDomainFeatures:
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

    return ClinicalDomainFeatures(
        patient_id=patient_id,
        domain="diabetes",
        extracted_at=now,
        hba1c=hba1c_feat,
        egfr=EGFRTrajectoryFeature(available=False, status="unavailable", unit="mL/min/1.73m²"),
        systolic_bp=SystolicBPTrajectoryFeature(available=False, status="unavailable", unit="mmHg"),
        feature_vector={"hba1c_latest": latest_val} if hba1c_available else {},
    )


def test_sufficient_longitudinal_data_diabetes():
    features = build_mock_features(hba1c_count=3, latest_val=8.2, prev_val=7.6, annualized_rate=0.86)
    result = DiabetesRiskEstimator.evaluate(features)

    assert isinstance(result, RiskAssessmentResult)
    assert result.patient_id == "test-patient-dm"
    assert result.domain == ClinicalDomain.DIABETES
    assert result.estimator_id == "diabetes_hba1c_trajectory_v0_1"
    assert result.estimator_version == "0.1.0-foundation"
    assert result.data_sufficiency == DataSufficiencyStatus.SUFFICIENT
    assert result.calibration_status == CalibrationStatus.NOT_CALIBRATED
    assert result.risk_estimate is None
    assert result.confidence_interval is None

    # Check features used
    assert "hba1c_latest" in result.features_used
    assert result.features_used["hba1c_latest"].value == 8.2
    assert "hba1c_previous" in result.features_used
    assert result.features_used["hba1c_previous"].value == 7.6
    assert "hba1c_change" in result.features_used
    assert result.features_used["hba1c_change"].value == 0.6
    assert "hba1c_annualized_rate" in result.features_used
    assert result.features_used["hba1c_annualized_rate"].value == 0.86

    assert result.unavailable_inputs == []
    assert len(result.limitations) > 0
    assert any("calibration" in lim.lower() for lim in result.limitations)


def test_single_measurement_insufficient_history():
    features = build_mock_features(hba1c_count=1, latest_val=7.5)
    result = DiabetesRiskEstimator.evaluate(features)

    assert result.data_sufficiency == DataSufficiencyStatus.INSUFFICIENT
    assert result.calibration_status == CalibrationStatus.NOT_CALIBRATED
    assert result.risk_estimate is None
    assert "hba1c_latest" in result.features_used
    assert "hba1c_previous" not in result.features_used
    assert "hba1c_previous" in result.unavailable_inputs
    assert "hba1c_change" in result.unavailable_inputs
    assert "hba1c_annualized_rate" in result.unavailable_inputs
    assert any("1 hba1c observation" in lim.lower() for lim in result.limitations)


def test_unavailable_data_zero_measurements():
    features = build_mock_features(hba1c_available=False)
    result = DiabetesRiskEstimator.evaluate(features)

    assert result.data_sufficiency == DataSufficiencyStatus.UNAVAILABLE
    assert result.calibration_status == CalibrationStatus.INSUFFICIENT_MODEL
    assert result.risk_estimate is None
    assert len(result.features_used) == 0
    assert "hba1c_latest" in result.unavailable_inputs
    assert "hba1c_annualized_rate" in result.unavailable_inputs
    assert any("no hba1c observations" in lim.lower() for lim in result.limitations)


def test_identical_timestamps_zero_interval():
    features = build_mock_features(
        hba1c_count=2,
        latest_val=8.0,
        prev_val=7.9,
        time_interval_days=0.0,
        annualized_rate=None,
        status="identical_timestamps",
    )
    result = DiabetesRiskEstimator.evaluate(features)

    assert result.data_sufficiency == DataSufficiencyStatus.INSUFFICIENT
    assert result.calibration_status == CalibrationStatus.NOT_CALIBRATED
    assert result.risk_estimate is None
    assert "hba1c_latest" in result.features_used
    assert "hba1c_previous" in result.features_used
    assert "hba1c_change" in result.features_used
    assert "hba1c_annualized_rate" in result.unavailable_inputs
    assert any("identical timestamps" in lim.lower() for lim in result.limitations)


def test_estimator_determinism():
    features = build_mock_features(hba1c_count=2, latest_val=8.2, prev_val=7.6, annualized_rate=0.86)
    res1 = DiabetesRiskEstimator.evaluate(features)
    res2 = DiabetesRiskEstimator.evaluate(features)

    assert res1.data_sufficiency == res2.data_sufficiency
    assert res1.calibration_status == res2.calibration_status
    assert res1.risk_estimate == res2.risk_estimate
    assert res1.unavailable_inputs == res2.unavailable_inputs
    assert len(res1.features_used) == len(res2.features_used)
    for k in res1.features_used:
        assert res1.features_used[k].value == res2.features_used[k].value


def test_immutability_of_clinical_features():
    features = build_mock_features(hba1c_count=2, latest_val=8.2, prev_val=7.6, annualized_rate=0.86)
    snapshot = copy.deepcopy(features)

    DiabetesRiskEstimator.evaluate(features)

    assert features == snapshot
    assert features.hba1c.latest_value == snapshot.hba1c.latest_value
    assert features.hba1c.measurement_count == snapshot.hba1c.measurement_count


def test_unsupported_domain_raises():
    features = build_mock_features()
    with pytest.raises(ValueError, match="not active yet"):
        risk_assessment_engine.assess_features(features, ClinicalDomain.CHRONIC_KIDNEY_DISEASE)


def test_get_model_card():
    card = risk_assessment_engine.get_model_card(ClinicalDomain.DIABETES)
    assert card["estimator_id"] == "diabetes_hba1c_trajectory_v0_1"
    assert card["version"] == "0.1.0-foundation"
    assert card["calibration_status"] == "not_calibrated"
    assert "hba1c_latest" in card["input_features"]


@pytest.mark.asyncio
async def test_api_assess_patient_diabetes_risk_flow_and_audit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ingest the standard sample FHIR bundle
        sample_res = await ac.get("/api/v1/emr/sample-fhir")
        bundle = sample_res.json()
        ingest_res = await ac.post("/api/v1/emr/ingest", json=bundle)
        assert ingest_res.status_code == 201
        patient_id = ingest_res.json()["patient_record"]["patient_id"]

        # Call the diabetes risk assessment endpoint
        res = await ac.get(
            f"/api/v1/risk/patients/{patient_id}/diabetes",
            headers={"X-Actor-ID": "dr-endocrinologist-01"},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["patient_id"] == patient_id
        assert data["domain"] == "diabetes"
        assert data["estimator_id"] == "diabetes_hba1c_trajectory_v0_1"
        assert data["estimator_version"] == "0.1.0-foundation"
        assert data["data_sufficiency"] == "sufficient_data"
        assert data["calibration_status"] == "not_calibrated"
        assert data["risk_estimate"] is None
        assert data["confidence_interval"] is None
        assert data["disclaimer"] != ""

        # Validate extracted features were correctly fed into estimator
        features_used = data["features_used"]
        assert features_used["hba1c_latest"]["value"] == 8.2
        assert features_used["hba1c_previous"]["value"] == 7.6
        assert features_used["hba1c_change"]["value"] == 0.6
        assert "hba1c_annualized_rate" in features_used

        # Check HIPAA audit event
        events = audit_service.get_recent_events()
        risk_events = [e for e in events if e.action == "assess_diabetes_risk" and e.resource_id == patient_id]
        assert len(risk_events) >= 1
        latest_event = risk_events[-1]
        assert latest_event.actor_id == "dr-endocrinologist-01"
        assert latest_event.metadata["data_sufficiency"] == "sufficient_data"
        assert latest_event.metadata["calibration_status"] == "not_calibrated"


@pytest.mark.asyncio
async def test_api_assess_patient_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/risk/patients/nonexistent-pat-404/diabetes")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_evaluate_features_direct():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        features = build_mock_features(hba1c_count=2, latest_val=7.8, prev_val=7.2)
        res = await ac.post("/api/v1/risk/evaluate/diabetes", json=features.model_dump(mode="json"))
        assert res.status_code == 200
        data = res.json()
        assert data["data_sufficiency"] == "sufficient_data"
        assert data["calibration_status"] == "not_calibrated"
        assert data["features_used"]["hba1c_latest"]["value"] == 7.8


@pytest.mark.asyncio
async def test_api_capabilities_and_model_card():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        cap_res = await ac.get("/api/v1/risk/capabilities")
        assert cap_res.status_code == 200
        assert "diabetes" in cap_res.json()["supported_domains"]

        mc_res = await ac.get("/api/v1/risk/models/diabetes")
        assert mc_res.status_code == 200
        assert mc_res.json()["estimator_id"] == "diabetes_hba1c_trajectory_v0_1"
