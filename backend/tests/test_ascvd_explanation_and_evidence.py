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
)
from app.schemas.features import ClinicalDomainFeatures
from app.schemas.risk import (
    RiskAssessmentResult,
    DataSufficiencyStatus,
    CalibrationStatus,
)
from app.schemas.explanation import (
    ASCVDExplanationContext,
    ExplanationBiomarkerFact,
)
from app.schemas.evidence import (
    ClinicalEvidenceReference,
    EvidenceStatus,
    EvidenceDomainCategory,
)
from app.clinical.features import extract_clinical_features
from app.clinical.estimators.ascvd import ASCVDRiskEstimator
from app.clinical.explanation import build_ascvd_explanation_context
from app.clinical.evidence.registry import (
    EVIDENCE_SOURCE_REGISTRY,
    VERIFIED_EVIDENCE_REFERENCES,
)
from app.clinical.evidence.provider import curated_evidence_provider
from app.services.emr_ingestion import emr_ingestion_service
from app.services.explanation_service import explanation_service
from app.services.evidence_service import evidence_service


def build_complete_ascvd_record(patient_id: str = "PT-ASCVD-EXPLAIN-01") -> NormalizedPatientRecord:
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


def test_1_build_ascvd_explanation_context_all_features_grounded():
    record = build_complete_ascvd_record("PT-ASCVD-EXPLAIN-01")
    features = extract_clinical_features(record, domain="cardiovascular")
    assessment = ASCVDRiskEstimator.evaluate(features)

    context = build_ascvd_explanation_context(assessment=assessment, features=features)

    assert isinstance(context, ASCVDExplanationContext)
    assert context.patient_id == "PT-ASCVD-EXPLAIN-01"
    assert context.domain == ClinicalDomain.CARDIOVASCULAR
    assert context.estimator_id == "ascvd_pooled_cohort_v0_1"
    assert context.data_sufficiency == DataSufficiencyStatus.SUFFICIENT
    assert context.calibration_status == CalibrationStatus.NOT_CALIBRATED

    # Invariant: Calibrated score must be strictly None
    assert context.calibrated_risk_score is None
    assert context.is_statistically_calibrated is False

    # Core ASCVD factors
    assert context.age_years == 57
    assert context.age_available is True
    assert context.gender == "female"
    assert context.gender_available is True

    assert context.systolic_bp.is_available is True
    assert context.systolic_bp.value == 144.0
    assert context.systolic_bp.unit == "mmHg"
    assert context.systolic_bp_mean == 141.0
    assert context.systolic_bp_count == 2

    assert context.total_cholesterol.is_available is True
    assert context.total_cholesterol.value == 210.0
    assert context.total_cholesterol.unit == "mg/dL"

    assert context.hdl_cholesterol.is_available is True
    assert context.hdl_cholesterol.value == 52.0
    assert context.hdl_cholesterol.unit == "mg/dL"

    assert context.smoking_status == "current_smoker"
    assert context.smoking_status_available is True

    assert context.has_diabetes is True
    assert context.diabetes_status_available is True

    # Regulatory and safety guards
    assert context.is_diagnostic_claim is False
    assert context.treatment_recommendations_allowed is False
    assert "Strictly non-diagnostic and non-prescriptive" in context.non_diagnostic_disclaimer
    assert "statin" in context.non_diagnostic_disclaimer.lower()


def test_2_build_ascvd_explanation_context_missing_features_preserved_without_imputation():
    # Build record missing HDL and smoking status
    record = build_complete_ascvd_record("PT-ASCVD-PARTIAL-02")
    del record.longitudinal_biomarkers["hdl_cholesterol"]
    record.conditions = [c for c in record.conditions if not c.icd10_code.startswith("F17")]

    features = extract_clinical_features(record, domain="cardiovascular")
    assessment = ASCVDRiskEstimator.evaluate(features)

    context = build_ascvd_explanation_context(assessment=assessment, features=features)

    assert context.data_sufficiency == DataSufficiencyStatus.INSUFFICIENT
    assert context.calibrated_risk_score is None
    assert context.is_statistically_calibrated is False

    # HDL must be unavailable, not imputed
    assert context.hdl_cholesterol.is_available is False
    assert context.hdl_cholesterol.value is None

    # Smoking must be unavailable, not imputed
    assert context.smoking_status_available is False
    assert context.smoking_status is None

    # Missing inputs list
    assert "hdl_cholesterol" in context.unavailable_inputs
    assert "smoking_status" in context.unavailable_inputs


def test_3_build_ascvd_explanation_context_completely_absent_features():
    # Create empty features with ascvd = None
    empty_features = ClinicalDomainFeatures(
        patient_id="PT-ASCVD-EMPTY-03",
        domain="cardiovascular",
        extracted_at=datetime.now(timezone.utc),
        hba1c=extract_clinical_features(
            NormalizedPatientRecord(
                patient_id="PT-ASCVD-EMPTY-03",
                gender=None,
                birth_date=None,
                longitudinal_biomarkers={},
                conditions=[],
                medications=[],
                clinical_notes=[],
                clinical_domain_readiness={},
                total_biomarker_measurements=0,
            )
        ).hba1c,
        egfr=extract_clinical_features(
            NormalizedPatientRecord(
                patient_id="PT-ASCVD-EMPTY-03",
                gender=None,
                birth_date=None,
                longitudinal_biomarkers={},
                conditions=[],
                medications=[],
                clinical_notes=[],
                clinical_domain_readiness={},
                total_biomarker_measurements=0,
            )
        ).egfr,
        systolic_bp=extract_clinical_features(
            NormalizedPatientRecord(
                patient_id="PT-ASCVD-EMPTY-03",
                gender=None,
                birth_date=None,
                longitudinal_biomarkers={},
                conditions=[],
                medications=[],
                clinical_notes=[],
                clinical_domain_readiness={},
                total_biomarker_measurements=0,
            )
        ).systolic_bp,
        ascvd=None,
    )
    assessment = ASCVDRiskEstimator.evaluate(empty_features)
    context = build_ascvd_explanation_context(assessment=assessment, features=empty_features)

    assert context.data_sufficiency == DataSufficiencyStatus.UNAVAILABLE
    assert context.calibrated_risk_score is None
    assert context.systolic_bp.is_available is False
    assert context.total_cholesterol.is_available is False
    assert context.hdl_cholesterol.is_available is False
    assert context.age_available is False
    assert context.gender_available is False


def test_4_ascvd_explanation_context_immutability_and_determinism():
    record = build_complete_ascvd_record("PT-ASCVD-DETERMINISTIC")
    features = extract_clinical_features(record, domain="cardiovascular")
    assessment = ASCVDRiskEstimator.evaluate(features)

    features_copy = copy.deepcopy(features)
    assessment_copy = copy.deepcopy(assessment)

    fixed_time = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    ctx1 = build_ascvd_explanation_context(
        assessment=assessment, features=features, context_id="ctx-test-fixed", now=fixed_time
    )
    ctx2 = build_ascvd_explanation_context(
        assessment=assessment, features=features, context_id="ctx-test-fixed", now=fixed_time
    )

    # Immutability
    assert features == features_copy
    assert assessment == assessment_copy

    # Determinism
    assert ctx1.model_dump() == ctx2.model_dump()


def test_5_explanation_service_cardiovascular_patient_lookup():
    record = build_complete_ascvd_record("PT-ASCVD-SVC-01")
    emr_ingestion_service._patient_repository["PT-ASCVD-SVC-01"] = record

    context = explanation_service.get_cardiovascular_context_for_patient("PT-ASCVD-SVC-01")

    assert context.patient_id == "PT-ASCVD-SVC-01"
    assert context.domain == ClinicalDomain.CARDIOVASCULAR
    assert context.data_sufficiency == DataSufficiencyStatus.SUFFICIENT
    assert context.calibrated_risk_score is None


def test_6_explanation_service_unknown_patient_raises_value_error():
    with pytest.raises(ValueError) as excinfo:
        explanation_service.get_cardiovascular_context_for_patient("PT-DEFINITELY-NONEXISTENT")
    assert "not found in clinical repository" in str(excinfo.value)


def test_7_curated_evidence_provider_cardiovascular_retrieval():
    # Verify ACC/AHA 2019 evidence is retrieved for cardiovascular domain
    refs = curated_evidence_provider.get_references_by_domain(ClinicalDomain.CARDIOVASCULAR)
    assert len(refs) >= 1

    acc_ref = next((r for r in refs if r.source_id == "ACC-AHA-PPCVD-2019"), None)
    assert acc_ref is not None
    assert acc_ref.evidence_id == "ev-acc-2019-primary-prevention-cvd"
    assert "American College of Cardiology" in acc_ref.organization
    assert acc_ref.evidence_status == EvidenceStatus.VERIFIED
    assert acc_ref.official_url.startswith("https://www.ahajournals.org")
    assert acc_ref.recommendation_identifier is None  # Safety invariant: strictly un-fabricated
    assert "prescribe" not in acc_ref.scope_description.lower()


@pytest.mark.asyncio
async def test_8_api_get_cardiovascular_evidence_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/evidence/cardiovascular")
        assert res.status_code == 200
        data = res.json()

        assert data["domain"] == "cardiovascular"
        assert data["total_references"] >= 1
        assert data["provider_id"] == "curated_evidence_provider_v1"
        assert len(data["references"]) >= 1

        ref = data["references"][0]
        assert ref["source_id"] == "ACC-AHA-PPCVD-2019"
        assert ref["recommendation_identifier"] is None
        assert "Arnett DK" in ref["citation_text"]
        assert "decision support only" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_9_api_get_cardiovascular_explanation_context_endpoint():
    record = build_complete_ascvd_record("PT-ASCVD-API-01")
    emr_ingestion_service._patient_repository["PT-ASCVD-API-01"] = record

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/risk/patients/PT-ASCVD-API-01/cardiovascular/explanation-context",
            headers={"X-Actor-ID": "dr-cardiologist-42"},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["patient_id"] == "PT-ASCVD-API-01"
        assert data["domain"] == "cardiovascular"
        assert data["data_sufficiency"] == "sufficient_data"
        assert data["calibration_status"] == "not_calibrated"
        assert data["calibrated_risk_score"] is None
        assert data["is_statistically_calibrated"] is False

        # Verify factors
        assert data["age_years"] == 57
        assert data["gender"] == "female"
        assert data["systolic_bp"]["value"] == 144.0
        assert data["total_cholesterol"]["value"] == 210.0
        assert data["hdl_cholesterol"]["value"] == 52.0
        assert data["smoking_status"] == "current_smoker"
        assert data["has_diabetes"] is True

        # Safety disclaimer
        assert "non-diagnostic and non-prescriptive" in data["non_diagnostic_disclaimer"].lower()


@pytest.mark.asyncio
async def test_10_api_get_cardiovascular_explanation_context_unknown_patient_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/risk/patients/PT-ASCVD-DOES-NOT-EXIST/cardiovascular/explanation-context"
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_11_audit_logging_and_phi_isolation_cardiovascular_evidence():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/evidence/cardiovascular?patient_id=PT-ASCVD-AUDIT-01",
            headers={"X-Actor-ID": "dr-cvd-specialist-09"},
        )
        assert res.status_code == 200

        # Check HIPAA audit trail
        events = audit_service.get_recent_events()
        matching = [
            e for e in events
            if e.action == "retrieve_cardiovascular_evidence"
            and e.resource_id == "PT-ASCVD-AUDIT-01"
            and e.actor_id == "dr-cvd-specialist-09"
        ]
        assert len(matching) >= 1
        audit_event = matching[-1]
        assert audit_event.status == "success"
        assert "evidence_request_id" in audit_event.metadata
        assert "evidence_ids_returned" in audit_event.metadata
        assert len(audit_event.metadata["evidence_ids_returned"]) >= 1

        # PHI isolation: verify no patient notes or clinical free-text is logged
        audit_dump = audit_event.model_dump_json()
        assert "clinical_notes" not in audit_dump
        assert "resourceType" not in audit_dump


@pytest.mark.asyncio
async def test_12_audit_logging_and_phi_isolation_cardiovascular_explanation_context():
    record = build_complete_ascvd_record("PT-ASCVD-AUDIT-02")
    emr_ingestion_service._patient_repository["PT-ASCVD-AUDIT-02"] = record

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/risk/patients/PT-ASCVD-AUDIT-02/cardiovascular/explanation-context",
            headers={"X-Actor-ID": "dr-cvd-audit-reviewer"},
        )
        assert res.status_code == 200

        events = audit_service.get_recent_events()
        matching = [
            e for e in events
            if e.action == "get_cardiovascular_explanation_context"
            and e.resource_id == "PT-ASCVD-AUDIT-02"
            and e.actor_id == "dr-cvd-audit-reviewer"
        ]
        assert len(matching) >= 1
        audit_event = matching[-1]
        assert audit_event.status == "success"
        assert "context_id" in audit_event.metadata
        assert "assessment_id" in audit_event.metadata

        # PHI isolation
        audit_dump = audit_event.model_dump_json()
        assert "clinical_notes" not in audit_dump
        assert "birth_date" not in audit_dump
