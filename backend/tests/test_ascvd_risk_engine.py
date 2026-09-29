import copy
from datetime import datetime, date, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import ClinicalDomain
from app.core.audit import audit_service
from app.schemas.emr import (
    NormalizedPatientRecord,
    NormalizedBiomarkerPoint,
    NormalizedCondition,
    NormalizedMedication,
    NormalizedClinicalNote,
    PatientEMRPayload,
    EMRObservation,
    EMRCondition,
    ClinicalCoding,
)
from app.schemas.risk import (
    RiskAssessmentResult,
    DataSufficiencyStatus,
    CalibrationStatus,
)
from app.schemas.evidence import EvidenceDomainCategory
from app.clinical.features import (
    derive_lipid_feature,
    extract_smoking_status,
    extract_diabetes_history,
    derive_ascvd_features,
    extract_clinical_features,
)
from app.clinical.fhir_parser import ClinicalSemanticValidator
from app.clinical.estimators.ascvd import ASCVDRiskEstimator
from app.clinical.evidence.mapping import map_clinical_features_to_evidence_domains
from app.services.emr_ingestion import emr_ingestion_service
from app.services.risk_engine import risk_assessment_engine


def build_complete_ascvd_record(patient_id: str = "PT-ASCVD-COMPLETE") -> NormalizedPatientRecord:
    """Builds a verified clinical record containing all 7 core ASCVD parameters."""
    t1 = datetime(2025, 6, 1, 9, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)

    return NormalizedPatientRecord(
        patient_id=patient_id,
        gender="female",
        birth_date=date(1968, 5, 20),
        age_years=57,
        longitudinal_biomarkers={
            "systolic_bp": [
                NormalizedBiomarkerPoint(
                    observation_id="sbp-1",
                    biomarker_key="systolic_bp",
                    standard_name="Systolic Blood Pressure",
                    effective_datetime=t1,
                    value=138.0,
                    unit="mmHg",
                ),
                NormalizedBiomarkerPoint(
                    observation_id="sbp-2",
                    biomarker_key="systolic_bp",
                    standard_name="Systolic Blood Pressure",
                    effective_datetime=t2,
                    value=144.0,
                    unit="mmHg",
                ),
            ],
            "total_cholesterol": [
                NormalizedBiomarkerPoint(
                    observation_id="tc-1",
                    biomarker_key="total_cholesterol",
                    standard_name="Total Serum Cholesterol",
                    effective_datetime=t2,
                    value=210.0,
                    unit="mg/dL",
                ),
            ],
            "hdl_cholesterol": [
                NormalizedBiomarkerPoint(
                    observation_id="hdl-1",
                    biomarker_key="hdl_cholesterol",
                    standard_name="High-Density Lipoprotein (HDL)",
                    effective_datetime=t2,
                    value=52.0,
                    unit="mg/dL",
                ),
            ],
        },
        conditions=[
            NormalizedCondition(
                condition_id="c-smoke",
                icd10_code="F17.210",
                display_name="Nicotine dependence, cigarettes, uncomplicated",
                clinical_status="active",
                recorded_date=date(2023, 1, 10),
            ),
            NormalizedCondition(
                condition_id="c-dm",
                icd10_code="E11.9",
                display_name="Type 2 diabetes mellitus without complications",
                clinical_status="active",
                recorded_date=date(2022, 4, 15),
            ),
        ],
        medications=[],
        clinical_notes=[],
        clinical_domain_readiness={
            "diabetes": True,
            "cardiovascular": True,
            "chronic_kidney_disease": False,
            "cancer": False,
        },
        total_biomarker_measurements=4,
    )


def test_1_ascvd_feature_extraction_complete_record():
    record = build_complete_ascvd_record()
    ascvd_feats = derive_ascvd_features(record)

    assert ascvd_feats.patient_id == "PT-ASCVD-COMPLETE"
    assert ascvd_feats.age_available is True
    assert ascvd_feats.age_years == 57
    assert ascvd_feats.gender_available is True
    assert ascvd_feats.gender == "female"

    assert ascvd_feats.systolic_bp.available is True
    assert ascvd_feats.systolic_bp.latest_value == 144.0
    assert ascvd_feats.systolic_bp.mean == 141.0
    assert ascvd_feats.systolic_bp.measurement_count == 2

    assert ascvd_feats.total_cholesterol.available is True
    assert ascvd_feats.total_cholesterol.latest_value == 210.0

    assert ascvd_feats.hdl_cholesterol.available is True
    assert ascvd_feats.hdl_cholesterol.latest_value == 52.0

    assert ascvd_feats.smoking_status.available is True
    assert ascvd_feats.smoking_status.value == "current_smoker"

    assert ascvd_feats.diabetes_history.available is True
    assert ascvd_feats.diabetes_history.has_diabetes is True

    assert len(ascvd_feats.missing_required_features) == 0
    assert ascvd_feats.is_sufficient_for_ascvd is True


def test_2_missing_features_explicitly_flagged_without_imputation():
    # Record missing cholesterol and smoking status
    t = datetime(2026, 1, 15, tzinfo=timezone.utc)
    partial_rec = NormalizedPatientRecord(
        patient_id="PT-PARTIAL-CVD",
        gender="male",
        birth_date=date(1975, 1, 1),
        age_years=51,
        longitudinal_biomarkers={
            "systolic_bp": [
                NormalizedBiomarkerPoint(
                    observation_id="sbp-1",
                    biomarker_key="systolic_bp",
                    standard_name="Systolic BP",
                    effective_datetime=t,
                    value=130.0,
                    unit="mmHg",
                )
            ]
        },
        conditions=[],  # No smoking code, no diabetes code
    )

    ascvd_feats = derive_ascvd_features(partial_rec)

    assert ascvd_feats.total_cholesterol.available is False
    assert ascvd_feats.total_cholesterol.latest_value is None
    assert ascvd_feats.hdl_cholesterol.available is False
    assert ascvd_feats.smoking_status.available is False
    assert ascvd_feats.smoking_status.value is None

    assert "total_cholesterol" in ascvd_feats.missing_required_features
    assert "hdl_cholesterol" in ascvd_feats.missing_required_features
    assert "smoking_status" in ascvd_feats.missing_required_features
    assert ascvd_feats.is_sufficient_for_ascvd is False


def test_3_physiological_validation_cholesterol_out_of_bounds():
    # Total cholesterol below physiological min (30 mg/dL)
    payload_low = PatientEMRPayload(
        patient_id="PT-CHOL-ERR-1",
        observations=[
            EMRObservation(
                observation_id="obs-chol-low",
                code=ClinicalCoding(system="http://loinc.org", code="2093-3", display="Total Cholesterol"),
                effective_datetime=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
                value_numeric=12.0,  # Below minimum plausible of 30.0
                unit="mg/dL",
            )
        ]
    )
    rec, errors, warnings = ClinicalSemanticValidator.validate_and_normalize(payload_low)
    assert rec is None
    assert len(errors) >= 1
    assert errors[0].code == "PHYSIOLOGICAL_RANGE_EXCEEDED"
    assert "Total Serum Cholesterol" in errors[0].issue

    # Total cholesterol above physiological max (1500 mg/dL)
    payload_high = PatientEMRPayload(
        patient_id="PT-CHOL-ERR-2",
        observations=[
            EMRObservation(
                observation_id="obs-chol-high",
                code=ClinicalCoding(system="http://loinc.org", code="2093-3", display="Total Cholesterol"),
                effective_datetime=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
                value_numeric=2200.0,
                unit="mg/dL",
            )
        ]
    )
    rec2, errors2, warnings2 = ClinicalSemanticValidator.validate_and_normalize(payload_high)
    assert rec2 is None
    assert errors2[0].code == "PHYSIOLOGICAL_RANGE_EXCEEDED"


def test_4_physiological_validation_hdl_out_of_bounds():
    # HDL below physiological min (5.0 mg/dL)
    payload_hdl = PatientEMRPayload(
        patient_id="PT-HDL-ERR",
        observations=[
            EMRObservation(
                observation_id="obs-hdl-low",
                code=ClinicalCoding(system="http://loinc.org", code="2085-9", display="HDL"),
                effective_datetime=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
                value_numeric=1.5,
                unit="mg/dL",
            )
        ]
    )
    rec, errors, _ = ClinicalSemanticValidator.validate_and_normalize(payload_hdl)
    assert rec is None
    assert len(errors) >= 1
    assert errors[0].code == "PHYSIOLOGICAL_RANGE_EXCEEDED"
    assert "High-Density Lipoprotein" in errors[0].issue


def test_5_physiological_validation_lipid_fraction_inversion():
    # HDL fraction cannot be greater than or equal to Total Cholesterol
    t = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
    payload_inverted = PatientEMRPayload(
        patient_id="PT-LIPID-INVERT",
        observations=[
            EMRObservation(
                observation_id="obs-tc",
                code=ClinicalCoding(system="http://loinc.org", code="2093-3", display="Total Cholesterol"),
                effective_datetime=t,
                value_numeric=150.0,
                unit="mg/dL",
            ),
            EMRObservation(
                observation_id="obs-hdl",
                code=ClinicalCoding(system="http://loinc.org", code="2085-9", display="HDL Cholesterol"),
                effective_datetime=t,
                value_numeric=175.0,  # HDL > Total Cholesterol: physiologically impossible
                unit="mg/dL",
            ),
        ]
    )
    rec, errors, _ = ClinicalSemanticValidator.validate_and_normalize(payload_inverted)
    assert rec is None
    inverted_err = [e for e in errors if e.code == "LIPID_FRACTION_INVERSION"]
    assert len(inverted_err) == 1
    assert "must be strictly greater than HDL" in inverted_err[0].issue


def test_6_smoking_status_variations_handling():
    # Test former smoker (Z87.891)
    rec_former = NormalizedPatientRecord(
        patient_id="PT-SMOKE-FORMER",
        conditions=[
            NormalizedCondition(
                condition_id="c-z87",
                icd10_code="Z87.891",
                display_name="Personal history of nicotine dependence",
                clinical_status="resolved",
            )
        ],
    )
    smoke_feat = extract_smoking_status(rec_former)
    assert smoke_feat.available is True
    assert smoke_feat.value == "former_smoker"

    # Test never smoker (LOINC 72166-2 observation value = 0)
    rec_never = NormalizedPatientRecord(
        patient_id="PT-SMOKE-NEVER",
        longitudinal_biomarkers={
            "smoking_status": [
                NormalizedBiomarkerPoint(
                    observation_id="obs-smk",
                    biomarker_key="smoking_status",
                    standard_name="Tobacco smoking status",
                    effective_datetime=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    value=0.0,
                    unit="{score}",
                    loinc_code="72166-2",
                )
            ]
        },
    )
    smoke_never = extract_smoking_status(rec_never)
    assert smoke_never.available is True
    assert smoke_never.value == "never_smoker"


def test_7_diabetes_status_detection_sources():
    # Diabetes detected via medication (Metformin) even if condition absent
    rec_med = NormalizedPatientRecord(
        patient_id="PT-DM-MED",
        medications=[
            NormalizedMedication(
                medication_id="m-metformin",
                display_name="Metformin hydrochloride 500 MG",
                status="active",
            )
        ],
    )
    dm_feat = extract_diabetes_history(rec_med)
    assert dm_feat.available is True
    assert dm_feat.has_diabetes is True
    assert any("Metformin" in s for s in dm_feat.source_evidence)

    # Diabetes detected via lab (HbA1c >= 6.5%)
    rec_lab = NormalizedPatientRecord(
        patient_id="PT-DM-LAB",
        longitudinal_biomarkers={
            "hba1c": [
                NormalizedBiomarkerPoint(
                    observation_id="hba1c-high",
                    biomarker_key="hba1c",
                    standard_name="HbA1c",
                    effective_datetime=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    value=6.8,
                    unit="%",
                )
            ]
        },
    )
    dm_lab_feat = extract_diabetes_history(rec_lab)
    assert dm_lab_feat.available is True
    assert dm_lab_feat.has_diabetes is True
    assert any("6.8" in s for s in dm_lab_feat.source_evidence)


def test_8_ascvd_estimator_sufficient_features_safety():
    record = build_complete_ascvd_record()
    features = extract_clinical_features(record, domain="cardiovascular")

    result = ASCVDRiskEstimator.evaluate(features)

    assert result.patient_id == "PT-ASCVD-COMPLETE"
    assert result.domain == ClinicalDomain.CARDIOVASCULAR
    assert result.estimator_id == "ascvd_pooled_cohort_v0_1"
    assert result.estimator_version == "0.1.0-foundation"
    assert result.data_sufficiency == DataSufficiencyStatus.SUFFICIENT
    assert result.calibration_status == CalibrationStatus.NOT_CALIBRATED

    # Strict probability safety invariant: no fabricated numbers!
    assert result.risk_estimate is None
    assert result.confidence_interval is None

    # Confirm all 7 features documented in features_used
    assert "age" in result.features_used
    assert "gender" in result.features_used
    assert "systolic_bp" in result.features_used
    assert "total_cholesterol" in result.features_used
    assert "hdl_cholesterol" in result.features_used
    assert "smoking_status" in result.features_used
    assert "diabetes_status" in result.features_used

    # Limitations explicitly disclose uncalibrated status
    assert any("uncalibrated" in lim.lower() for lim in result.limitations)
    assert any("statin" in lim.lower() for lim in result.limitations)


def test_9_ascvd_estimator_insufficient_features_safety():
    # Only blood pressure present, lipids missing
    rec_incomplete = NormalizedPatientRecord(
        patient_id="PT-ASCVD-INCOMPLETE",
        gender="male",
        birth_date=date(1980, 2, 1),
        age_years=46,
        longitudinal_biomarkers={
            "systolic_bp": [
                NormalizedBiomarkerPoint(
                    observation_id="sbp-1",
                    biomarker_key="systolic_bp",
                    standard_name="Systolic BP",
                    effective_datetime=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    value=135.0,
                    unit="mmHg",
                )
            ]
        },
    )
    features = extract_clinical_features(rec_incomplete, domain="cardiovascular")
    result = ASCVDRiskEstimator.evaluate(features)

    assert result.data_sufficiency == DataSufficiencyStatus.INSUFFICIENT
    assert result.calibration_status == CalibrationStatus.NOT_CALIBRATED
    assert result.risk_estimate is None
    assert "total_cholesterol" in result.unavailable_inputs
    assert "hdl_cholesterol" in result.unavailable_inputs
    assert "smoking_status" in result.unavailable_inputs


def test_10_ascvd_estimator_unavailable_inputs():
    # Record with zero CVD features (only HbA1c present)
    rec_no_cvd = NormalizedPatientRecord(
        patient_id="PT-NO-CVD",
        longitudinal_biomarkers={
            "hba1c": [
                NormalizedBiomarkerPoint(
                    observation_id="hba1c-1",
                    biomarker_key="hba1c",
                    standard_name="HbA1c",
                    effective_datetime=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    value=7.0,
                    unit="%",
                )
            ]
        },
    )
    features = extract_clinical_features(rec_no_cvd, domain="cardiovascular")
    result = ASCVDRiskEstimator.evaluate(features)

    assert result.data_sufficiency == DataSufficiencyStatus.UNAVAILABLE
    assert result.calibration_status == CalibrationStatus.INSUFFICIENT_MODEL
    assert result.risk_estimate is None
    assert len(result.features_used) == 0


def test_11_feature_immutability():
    record = build_complete_ascvd_record()
    features = extract_clinical_features(record, domain="cardiovascular")
    snapshot = copy.deepcopy(features)

    result = ASCVDRiskEstimator.evaluate(features)

    assert features == snapshot, "Estimator must not mutate input features"


def test_12_cardiovascular_evidence_mapping():
    # SBP, cholesterol, smoking map to CARDIOVASCULAR_RISK_EXPANSION
    domains = map_clinical_features_to_evidence_domains(
        ["systolic_bp_latest", "total_cholesterol_latest", "hdl_cholesterol_latest"]
    )
    assert EvidenceDomainCategory.CARDIOVASCULAR_RISK_EXPANSION in domains


def test_13_risk_engine_cardiovascular_model_card():
    card = risk_assessment_engine.get_model_card(ClinicalDomain.CARDIOVASCULAR)
    assert card["estimator_id"] == "ascvd_pooled_cohort_v0_1"
    assert card["domain"] == "cardiovascular"
    assert card["calibration_status"] == "not_calibrated"
    assert "total_cholesterol" in card["input_features"]
    assert "hdl_cholesterol" in card["input_features"]


@pytest.mark.asyncio
async def test_14_api_assess_cardiovascular_risk_flow_and_audit():
    # Ingest record
    record = build_complete_ascvd_record("PT-API-CVD-TEST")
    emr_ingestion_service._patient_repository["PT-API-CVD-TEST"] = record

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/risk/patients/PT-API-CVD-TEST/cardiovascular",
            headers={"X-Actor-ID": "dr-cardiologist-01"},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["patient_id"] == "PT-API-CVD-TEST"
        assert data["domain"] == "cardiovascular"
        assert data["estimator_id"] == "ascvd_pooled_cohort_v0_1"
        assert data["data_sufficiency"] == "sufficient_data"
        assert data["calibration_status"] == "not_calibrated"
        assert data["risk_estimate"] is None

        # Verify audit trail
        events = audit_service.get_recent_events()
        matching = [
            e for e in events
            if e.action == "assess_cardiovascular_risk"
            and e.resource_id == "PT-API-CVD-TEST"
            and e.actor_id == "dr-cardiologist-01"
        ]
        assert len(matching) >= 1
        audit_event = matching[-1]
        assert audit_event.status == "success"
        assert audit_event.metadata["estimator_id"] == "ascvd_pooled_cohort_v0_1"


@pytest.mark.asyncio
async def test_15_api_cardiovascular_unknown_patient():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/risk/patients/PT-UNKNOWN-CVD-999/cardiovascular")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_16_api_evaluate_cardiovascular_direct_features():
    record = build_complete_ascvd_record("PT-DIRECT-CVD")
    features = extract_clinical_features(record, domain="cardiovascular")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/risk/evaluate/cardiovascular",
            json=features.model_dump(mode="json"),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["domain"] == "cardiovascular"
        assert data["data_sufficiency"] == "sufficient_data"
        assert data["risk_estimate"] is None
