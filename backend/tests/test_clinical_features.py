import copy
import pytest
from datetime import datetime, timezone, timedelta
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.schemas.emr import (
    NormalizedPatientRecord,
    NormalizedBiomarkerPoint,
    NormalizedCondition,
    NormalizedMedication,
)
from app.clinical.features import (
    derive_hba1c_trajectory,
    derive_egfr_trajectory,
    derive_systolic_bp_trajectory,
    extract_clinical_features,
)
from app.services.emr_ingestion import emr_ingestion_service


def create_point(key: str, name: str, dt_str: str, val: float, unit: str) -> NormalizedBiomarkerPoint:
    return NormalizedBiomarkerPoint(
        observation_id=f"obs-{key}-{val}",
        biomarker_key=key,
        standard_name=name,
        effective_datetime=datetime.fromisoformat(dt_str.replace("Z", "+00:00")),
        value=val,
        unit=unit,
        loinc_code="test-code",
    )


def test_hba1c_trajectory_derivation():
    # 3 points spanning ~1.5 years: 7.1 -> 7.6 -> 8.2
    pts = [
        create_point("hba1c", "Hemoglobin A1c", "2024-09-15T09:00:00Z", 7.1, "%"),
        create_point("hba1c", "Hemoglobin A1c", "2025-06-12T09:15:00Z", 7.6, "%"),
        create_point("hba1c", "Hemoglobin A1c", "2026-02-20T08:45:00Z", 8.2, "%"),
    ]

    feat = derive_hba1c_trajectory(pts)
    assert feat.available is True
    assert feat.status == "available"
    assert feat.measurement_count == 3
    assert feat.latest_value == 8.2
    assert feat.previous_value == 7.6
    assert feat.absolute_change == 0.6
    assert feat.time_interval_days is not None
    assert feat.time_interval_days > 200  # ~253 days between June 2025 and Feb 2026
    assert feat.annualized_rate_of_change is not None
    # 0.6 over ~0.69 years = ~0.86% per year
    assert 0.7 < feat.annualized_rate_of_change < 1.1
    assert feat.unit == "%"


def test_egfr_trajectory_and_slope_derivation():
    # 3 points showing progressive renal decline: 64 -> 58 -> 52 over ~1.4 years
    pts = [
        create_point("egfr", "eGFR", "2024-09-15T09:00:00Z", 64.0, "mL/min/1.73m²"),
        create_point("egfr", "eGFR", "2025-06-12T09:00:00Z", 58.0, "mL/min/1.73m²"),
        create_point("egfr", "eGFR", "2026-02-20T08:45:00Z", 52.0, "mL/min/1.73m²"),
    ]

    feat = derive_egfr_trajectory(pts)
    assert feat.available is True
    assert feat.status == "available"
    assert feat.measurement_count == 3
    assert feat.latest_value == 52.0
    assert feat.previous_value == 58.0
    assert feat.absolute_change == -6.0
    assert feat.time_interval_days is not None
    assert feat.annualized_slope is not None
    # Annual decline of approx -8.3 mL/min/1.73m²/year
    assert feat.annualized_slope < 0.0
    assert -12.0 < feat.annualized_slope < -5.0
    assert feat.unit == "mL/min/1.73m²"


def test_systolic_bp_mean_and_variability():
    # Readings: 130, 140, 150
    pts = [
        create_point("systolic_bp", "Systolic BP", "2026-01-10T08:00:00Z", 130.0, "mmHg"),
        create_point("systolic_bp", "Systolic BP", "2026-01-15T08:00:00Z", 140.0, "mmHg"),
        create_point("systolic_bp", "Systolic BP", "2026-01-20T08:00:00Z", 150.0, "mmHg"),
    ]

    feat = derive_systolic_bp_trajectory(pts)
    assert feat.available is True
    assert feat.status == "available"
    assert feat.measurement_count == 3
    assert feat.latest_value == 150.0
    assert feat.mean == 140.0
    assert feat.standard_deviation == 10.0
    assert feat.unit == "mmHg"


def test_insufficient_history_single_measurement():
    hba1c_single = [create_point("hba1c", "HbA1c", "2026-01-10T08:00:00Z", 7.4, "%")]
    feat_h = derive_hba1c_trajectory(hba1c_single)
    assert feat_h.available is True
    assert feat_h.status == "single_measurement"
    assert feat_h.measurement_count == 1
    assert feat_h.latest_value == 7.4
    assert feat_h.previous_value is None
    assert feat_h.absolute_change is None
    assert feat_h.time_interval_days is None
    assert feat_h.annualized_rate_of_change is None

    egfr_single = [create_point("egfr", "eGFR", "2026-01-10T08:00:00Z", 65.0, "mL/min/1.73m²")]
    feat_e = derive_egfr_trajectory(egfr_single)
    assert feat_e.available is True
    assert feat_e.status == "single_measurement"
    assert feat_e.measurement_count == 1
    assert feat_e.latest_value == 65.0
    assert feat_e.previous_value is None
    assert feat_e.annualized_slope is None

    sbp_single = [create_point("systolic_bp", "Systolic BP", "2026-01-10T08:00:00Z", 136.0, "mmHg")]
    feat_s = derive_systolic_bp_trajectory(sbp_single)
    assert feat_s.available is True
    assert feat_s.status == "single_measurement"
    assert feat_s.measurement_count == 1
    assert feat_s.latest_value == 136.0
    assert feat_s.mean == 136.0
    assert feat_s.standard_deviation is None


def test_insufficient_history_zero_measurements():
    feat_h = derive_hba1c_trajectory([])
    assert feat_h.available is False
    assert feat_h.status == "insufficient_history"
    assert feat_h.measurement_count == 0
    assert feat_h.latest_value is None

    feat_e = derive_egfr_trajectory([])
    assert feat_e.available is False
    assert feat_e.status == "insufficient_history"

    feat_s = derive_systolic_bp_trajectory([])
    assert feat_s.available is False
    assert feat_s.status == "insufficient_history"


def test_identical_timestamps_prevents_division_by_zero():
    # Two HbA1c entries recorded at the exact same second
    same_dt = "2026-01-10T08:00:00Z"
    pts = [
        create_point("hba1c", "HbA1c", same_dt, 7.0, "%"),
        create_point("hba1c", "HbA1c", same_dt, 7.2, "%"),
    ]

    feat = derive_hba1c_trajectory(pts)
    assert feat.available is True
    assert feat.status == "identical_timestamps"
    assert feat.time_interval_days == 0.0
    assert feat.annualized_rate_of_change is None  # Handled safely without ZeroDivisionError
    assert feat.absolute_change == 0.2

    # Two eGFR entries at identical timestamp
    pts_e = [
        create_point("egfr", "eGFR", same_dt, 60.0, "mL/min/1.73m²"),
        create_point("egfr", "eGFR", same_dt, 62.0, "mL/min/1.73m²"),
    ]
    feat_e = derive_egfr_trajectory(pts_e)
    assert feat_e.available is True
    assert feat_e.status == "identical_timestamps"
    assert feat_e.annualized_slope is None


def test_original_normalized_measurements_remain_unchanged():
    pts_original = [
        create_point("hba1c", "Hemoglobin A1c", "2025-01-15T09:00:00Z", 7.1, "%"),
        create_point("hba1c", "Hemoglobin A1c", "2026-01-15T09:00:00Z", 7.8, "%"),
    ]
    # Deep copy to check immutability
    pts_copy = copy.deepcopy(pts_original)

    record = NormalizedPatientRecord(
        patient_id="PT-IMMUTABLE-TEST",
        gender="female",
        longitudinal_biomarkers={"hba1c": pts_original},
        conditions=[],
        medications=[],
        clinical_notes=[],
        total_biomarker_measurements=2,
    )

    # Execute feature extraction
    features = extract_clinical_features(record)

    # Verify features were computed
    assert features.hba1c.available is True
    assert features.hba1c.latest_value == 7.8

    # Verify original points inside record were NOT mutated
    assert len(record.longitudinal_biomarkers["hba1c"]) == 2
    assert record.longitudinal_biomarkers["hba1c"][0].value == pts_copy[0].value
    assert record.longitudinal_biomarkers["hba1c"][0].effective_datetime == pts_copy[0].effective_datetime
    assert record.longitudinal_biomarkers["hba1c"][1].value == pts_copy[1].value
    assert record.longitudinal_biomarkers["hba1c"][1].effective_datetime == pts_copy[1].effective_datetime


@pytest.mark.asyncio
async def test_end_to_end_feature_extraction_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ingest the standard sample FHIR bundle
        sample_res = await ac.get("/api/v1/emr/sample-fhir")
        bundle = sample_res.json()
        ingest_res = await ac.post("/api/v1/emr/ingest", json=bundle)
        assert ingest_res.status_code == 201
        pat_id = ingest_res.json()["patient_record"]["patient_id"]

        # Call the features endpoint
        feat_res = await ac.get(f"/api/v1/emr/patients/{pat_id}/features")
        assert feat_res.status_code == 200
        feat_data = feat_res.json()

        assert feat_data["patient_id"] == pat_id
        assert feat_data["hba1c"]["available"] is True
        assert feat_data["hba1c"]["latest_value"] == 8.2
        assert feat_data["hba1c"]["previous_value"] == 7.6
        assert feat_data["hba1c"]["absolute_change"] == 0.6
        assert feat_data["hba1c"]["annualized_rate_of_change"] is not None

        assert feat_data["egfr"]["available"] is True
        assert feat_data["egfr"]["latest_value"] == 52.0
        assert feat_data["egfr"]["previous_value"] == 64.0
        assert feat_data["egfr"]["annualized_slope"] is not None
        assert feat_data["egfr"]["annualized_slope"] < 0  # Declining renal function

        assert feat_data["systolic_bp"]["available"] is True
        assert feat_data["systolic_bp"]["latest_value"] == 142.0
        assert feat_data["systolic_bp"]["mean"] == 142.0

        # Verify feature vector is populated
        f_vec = feat_data["feature_vector"]
        assert f_vec["hba1c_latest"] == 8.2
        assert f_vec["hba1c_change"] == 0.6
        assert f_vec["egfr_latest"] == 52.0
        assert f_vec["systolic_bp_latest"] == 142.0
