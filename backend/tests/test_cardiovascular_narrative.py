import json
import pytest
from datetime import datetime, date, timezone
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import ClinicalDomain
from app.core.audit import audit_service
from app.schemas.emr import (
    NormalizedPatientRecord,
    NormalizedBiomarkerPoint,
    NormalizedCondition,
)
from app.schemas.explanation import ASCVDExplanationContext
from app.schemas.narrative import ClinicalNarrativeExplanation
from app.schemas.risk import DataSufficiencyStatus
from app.clinical.prompt_builder import build_cardiovascular_narrative_prompt
from app.clinical.providers.base import (
    BaseLLMProvider,
    ProviderNotConfiguredError,
)
from app.clinical.providers.mock import MockLLMProvider
from app.services.emr_ingestion import emr_ingestion_service
from app.services.explanation_service import explanation_service
from app.services.narrative_service import (
    narrative_service,
    ClinicalNarrativeValidationError,
)


def build_complete_ascvd_record(patient_id: str = "PT-CVD-NARR-01") -> NormalizedPatientRecord:
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


class FaultyCVDProvider(BaseLLMProvider):
    def __init__(self, response_text: str):
        self._response_text = response_text

    @property
    def provider_name(self) -> str:
        return "faulty-cvd-test-provider"

    @property
    def model_name(self) -> str:
        return "faulty-cvd-v1"

    async def generate_structured_narrative(self, system_instruction: str, user_prompt: str) -> str:
        return self._response_text


def test_1_build_cardiovascular_narrative_prompt_grounding():
    record = build_complete_ascvd_record("PT-PROMPT-TEST-01")
    emr_ingestion_service._patient_repository["PT-PROMPT-TEST-01"] = record

    context = explanation_service.get_cardiovascular_context_for_patient("PT-PROMPT-TEST-01")
    system_instruction, user_prompt = build_cardiovascular_narrative_prompt(context)

    # Check critical system instruction constraints
    assert "strictly factual" in system_instruction.lower()
    assert "NO TREATMENT OR MEDICATION DIRECTIVES" in system_instruction
    assert "NO AUTONOMOUS DIAGNOSIS" in system_instruction
    assert "CALIBRATION SAFETY" in system_instruction

    # Check user prompt is grounded exclusively in verified context
    assert "Verified Clinical Explanation Context" in user_prompt
    assert "PT-PROMPT-TEST-01" in user_prompt
    assert '"calibrated_risk_score": null' in user_prompt
    assert '"value": 144.0' in user_prompt
    assert '"value": 210.0' in user_prompt
    assert '"value": 52.0' in user_prompt
    assert '"current_smoker"' in user_prompt

    # Safety: No raw notes, no doctor free-text
    assert "clinical_notes" not in user_prompt
    assert "Bundle" not in user_prompt


@pytest.mark.asyncio
async def test_2_cardiovascular_narrative_synthesis_end_to_end():
    record = build_complete_ascvd_record("PT-CVD-SYNTH-01")
    emr_ingestion_service._patient_repository["PT-CVD-SYNTH-01"] = record

    narrative = await narrative_service.generate_cardiovascular_narrative("PT-CVD-SYNTH-01")

    assert isinstance(narrative, ClinicalNarrativeExplanation)
    assert narrative.patient_id == "PT-CVD-SYNTH-01"
    assert narrative.domain == ClinicalDomain.CARDIOVASCULAR
    assert narrative.narrative_id.startswith("narr-cvd-")
    assert narrative.provider == "mock"

    # All 5 structured sections present and non-empty
    assert len(narrative.summary) > 20
    assert len(narrative.observed_trajectory) > 20
    assert len(narrative.data_limitations) > 20
    assert len(narrative.statistical_calibration_status) > 20
    assert len(narrative.disclaimer) > 20

    # Grounded content verification
    assert "144.0 mmHg" in narrative.observed_trajectory or "144.0 mmHg" in narrative.summary
    assert "210.0 mg/dL" in narrative.observed_trajectory or "210.0 mg/dL" in narrative.summary
    assert "uncalibrated" in narrative.statistical_calibration_status.lower()
    assert "non-diagnostic and non-prescriptive" in narrative.disclaimer.lower()


@pytest.mark.asyncio
async def test_3_insufficient_ascvd_data_narrative_synthesis():
    record = build_complete_ascvd_record("PT-CVD-PARTIAL-01")
    del record.longitudinal_biomarkers["hdl_cholesterol"]
    record.conditions = [c for c in record.conditions if not c.icd10_code.startswith("F17")]
    emr_ingestion_service._patient_repository["PT-CVD-PARTIAL-01"] = record

    narrative = await narrative_service.generate_cardiovascular_narrative("PT-CVD-PARTIAL-01")

    assert "partial" in narrative.summary.lower() or "missing" in narrative.summary.lower()
    assert "hdl_cholesterol" in narrative.data_limitations or "missing" in narrative.data_limitations.lower()
    assert "uncalibrated" in narrative.statistical_calibration_status.lower()


@pytest.mark.asyncio
async def test_4_safety_rejection_statin_medication_directive():
    record = build_complete_ascvd_record("PT-CVD-SAFETY-01")
    emr_ingestion_service._patient_repository["PT-CVD-SAFETY-01"] = record

    bad_payload = {
        "summary": "Patient has elevated cholesterol and blood pressure.",
        "observed_trajectory": "Total cholesterol is 210 mg/dL and SBP is 144 mmHg. Initiate statin therapy immediately.",
        "data_limitations": "None.",
        "statistical_calibration_status": "Estimator is uncalibrated.",
        "disclaimer": "Factual clinical explanation context for decision support only. Strictly non-diagnostic and non-prescriptive.",
    }
    faulty_provider = FaultyCVDProvider(json.dumps(bad_payload))

    with pytest.raises(ClinicalNarrativeValidationError) as excinfo:
        await narrative_service.generate_cardiovascular_narrative(
            patient_id="PT-CVD-SAFETY-01", provider_override=faulty_provider
        )
    assert "unauthorized cardiovascular medication or statin" in str(excinfo.value)


@pytest.mark.asyncio
async def test_5_safety_rejection_fabricated_ascvd_probability():
    record = build_complete_ascvd_record("PT-CVD-SAFETY-02")
    emr_ingestion_service._patient_repository["PT-CVD-SAFETY-02"] = record

    bad_payload = {
        "summary": "Cardiovascular risk review.",
        "observed_trajectory": "Blood pressure is 144 mmHg. Patient has a 10-year risk of 18.5% for ASCVD events.",
        "data_limitations": "None.",
        "statistical_calibration_status": "Estimator is uncalibrated.",
        "disclaimer": "Factual clinical explanation context for decision support only. Strictly non-diagnostic and non-prescriptive.",
    }
    faulty_provider = FaultyCVDProvider(json.dumps(bad_payload))

    with pytest.raises(ClinicalNarrativeValidationError) as excinfo:
        await narrative_service.generate_cardiovascular_narrative(
            patient_id="PT-CVD-SAFETY-02", provider_override=faulty_provider
        )
    assert "unauthorized numerical probability" in str(excinfo.value)


@pytest.mark.asyncio
async def test_6_safety_rejection_autonomous_diagnosis():
    record = build_complete_ascvd_record("PT-CVD-SAFETY-03")
    emr_ingestion_service._patient_repository["PT-CVD-SAFETY-03"] = record

    bad_payload = {
        "summary": "We diagnose the patient with essential hypertension and hyperlipidemia.",
        "observed_trajectory": "SBP is 144 mmHg.",
        "data_limitations": "None.",
        "statistical_calibration_status": "Estimator is uncalibrated.",
        "disclaimer": "Factual clinical explanation context for decision support only. Strictly non-diagnostic and non-prescriptive.",
    }
    faulty_provider = FaultyCVDProvider(json.dumps(bad_payload))

    with pytest.raises(ClinicalNarrativeValidationError) as excinfo:
        await narrative_service.generate_cardiovascular_narrative(
            patient_id="PT-CVD-SAFETY-03", provider_override=faulty_provider
        )
    assert "unauthorized autonomous diagnostic claims" in str(excinfo.value)


@pytest.mark.asyncio
async def test_7_safety_rejection_malformed_json():
    record = build_complete_ascvd_record("PT-CVD-SAFETY-04")
    emr_ingestion_service._patient_repository["PT-CVD-SAFETY-04"] = record

    faulty_provider = FaultyCVDProvider("Here is the patient narrative: looks good!")

    with pytest.raises(ClinicalNarrativeValidationError) as excinfo:
        await narrative_service.generate_cardiovascular_narrative(
            patient_id="PT-CVD-SAFETY-04", provider_override=faulty_provider
        )
    assert "could not be parsed as valid JSON" in str(excinfo.value)


@pytest.mark.asyncio
async def test_8_safety_rejection_missing_disclaimer():
    record = build_complete_ascvd_record("PT-CVD-SAFETY-05")
    emr_ingestion_service._patient_repository["PT-CVD-SAFETY-05"] = record

    bad_payload = {
        "summary": "Cardiovascular risk review.",
        "observed_trajectory": "SBP is 144 mmHg.",
        "data_limitations": "None.",
        "statistical_calibration_status": "Estimator is uncalibrated.",
        "disclaimer": "Standard report disclaimer.",  # Missing mandatory non-diagnostic notice
    }
    faulty_provider = FaultyCVDProvider(json.dumps(bad_payload))

    with pytest.raises(ClinicalNarrativeValidationError) as excinfo:
        await narrative_service.generate_cardiovascular_narrative(
            patient_id="PT-CVD-SAFETY-05", provider_override=faulty_provider
        )
    assert "mandatory non-diagnostic regulatory disclaimer" in str(excinfo.value)


@pytest.mark.asyncio
async def test_9_api_post_cardiovascular_narrative_endpoint():
    record = build_complete_ascvd_record("PT-CVD-API-NARR-01")
    emr_ingestion_service._patient_repository["PT-CVD-API-NARR-01"] = record

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/genai/narrative/patients/PT-CVD-API-NARR-01/cardiovascular",
            headers={"X-Actor-ID": "dr-cardiologist-99"},
        )
        assert res.status_code == 200
        data = res.json()

        assert data["patient_id"] == "PT-CVD-API-NARR-01"
        assert data["domain"] == "cardiovascular"
        assert data["narrative_id"].startswith("narr-cvd-")
        assert len(data["summary"]) > 0
        assert len(data["observed_trajectory"]) > 0
        assert len(data["data_limitations"]) > 0
        assert len(data["statistical_calibration_status"]) > 0
        assert "non-diagnostic and non-prescriptive" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_10_api_post_cardiovascular_narrative_patient_not_found_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/genai/narrative/patients/PT-NONEXISTENT-999/cardiovascular")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_11_audit_logging_and_phi_isolation_cardiovascular_narrative():
    record = build_complete_ascvd_record("PT-CVD-AUDIT-NARR-01")
    emr_ingestion_service._patient_repository["PT-CVD-AUDIT-NARR-01"] = record

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/genai/narrative/patients/PT-CVD-AUDIT-NARR-01/cardiovascular",
            headers={"X-Actor-ID": "dr-audit-officer"},
        )
        assert res.status_code == 200

        # Check audit service events
        events = audit_service.get_recent_events()
        matching = [
            e for e in events
            if e.action == "generate_cardiovascular_narrative"
            and e.resource_id == "PT-CVD-AUDIT-NARR-01"
            and e.actor_id == "dr-audit-officer"
        ]
        assert len(matching) >= 1
        event = matching[-1]
        assert event.status == "success"
        assert "narrative_id" in event.metadata
        assert "context_id" in event.metadata
        assert "assessment_id" in event.metadata
        assert "provider" in event.metadata

        # PHI isolation: No prompts, raw outputs, or clinical notes stored in audit log
        audit_json = event.model_dump_json()
        assert "prompt" not in audit_json
        assert "raw_output" not in audit_json
        assert "clinical_notes" not in audit_json
        assert "birth_date" not in audit_json


@pytest.mark.asyncio
async def test_12_api_get_cardiovascular_explanation_context_in_genai():
    record = build_complete_ascvd_record("PT-CVD-GENAI-CTX-01")
    emr_ingestion_service._patient_repository["PT-CVD-GENAI-CTX-01"] = record

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/genai/explanation-context/patients/PT-CVD-GENAI-CTX-01/cardiovascular")
        assert res.status_code == 200
        data = res.json()

        assert data["patient_id"] == "PT-CVD-GENAI-CTX-01"
        assert data["domain"] == "cardiovascular"
        assert data["calibrated_risk_score"] is None
        assert data["is_statistically_calibrated"] is False
