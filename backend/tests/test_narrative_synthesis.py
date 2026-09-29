import copy
import json
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings, ClinicalDomain
from app.core.audit import audit_service
from app.schemas.features import (
    ClinicalDomainFeatures,
    HbA1cTrajectoryFeature,
    EGFRTrajectoryFeature,
    SystolicBPTrajectoryFeature,
)
from app.schemas.explanation import (
    AIExplanationContext,
    ExplanationBiomarkerFact,
    ExplanationTrajectorySummary,
)
from app.schemas.risk import DataSufficiencyStatus, CalibrationStatus
from app.clinical.prompt_builder import build_diabetes_narrative_prompt
from app.clinical.providers.base import (
    BaseLLMProvider,
    ProviderNotConfiguredError,
    LLMProviderError,
)
from app.clinical.providers.mock import MockLLMProvider
from app.clinical.providers.factory import get_llm_provider
from app.services.narrative_service import (
    narrative_service,
    ClinicalNarrativeValidationError,
)


def create_mock_explanation_context(
    patient_id: str = "PT-NARR-TEST-01",
    data_sufficiency: DataSufficiencyStatus = DataSufficiencyStatus.SUFFICIENT,
    is_calibrated: bool = False,
    hba1c_latest: float = 8.2,
    hba1c_prev: float = 7.6,
    hba1c_change: float = 0.6,
    hba1c_rate: float = 0.86,
    count: int = 3,
) -> AIExplanationContext:
    now = datetime.now(timezone.utc)
    return AIExplanationContext(
        context_id="ctx-dm-mock-1234",
        patient_id=patient_id,
        assessment_id="assess-dm-mock-5678",
        domain=ClinicalDomain.DIABETES,
        context_generated_at=now,
        assessment_timestamp=now,
        estimator_id="diabetes_hba1c_trajectory_v0_1",
        estimator_version="0.1.0-foundation",
        data_sufficiency=data_sufficiency,
        calibration_status=CalibrationStatus.NOT_CALIBRATED if not is_calibrated else CalibrationStatus.CALIBRATED,
        calibrated_risk_score=None if not is_calibrated else 0.25,
        is_statistically_calibrated=is_calibrated,
        latest_hba1c=ExplanationBiomarkerFact(
            feature_name="hba1c_latest",
            is_available=True,
            value=hba1c_latest,
            unit="%",
            source_timestamp=now,
            description="Most recent glycated hemoglobin observation",
        ),
        previous_hba1c=ExplanationBiomarkerFact(
            feature_name="hba1c_previous",
            is_available=(data_sufficiency == DataSufficiencyStatus.SUFFICIENT),
            value=hba1c_prev if data_sufficiency == DataSufficiencyStatus.SUFFICIENT else None,
            unit="%",
            source_timestamp=now if data_sufficiency == DataSufficiencyStatus.SUFFICIENT else None,
            description="Preceding glycated hemoglobin observation",
        ),
        absolute_change=ExplanationBiomarkerFact(
            feature_name="hba1c_change",
            is_available=(data_sufficiency == DataSufficiencyStatus.SUFFICIENT),
            value=hba1c_change if data_sufficiency == DataSufficiencyStatus.SUFFICIENT else None,
            unit="%",
            description="Absolute difference between consecutive measurements",
        ),
        annualized_rate=ExplanationBiomarkerFact(
            feature_name="hba1c_annualized_rate",
            is_available=(data_sufficiency == DataSufficiencyStatus.SUFFICIENT),
            value=hba1c_rate if data_sufficiency == DataSufficiencyStatus.SUFFICIENT else None,
            unit="%/year",
            description="Annualized rate of change across temporal interval",
        ),
        trajectory_summary=ExplanationTrajectorySummary(
            measurement_count=count,
            time_interval_days=253.0 if data_sufficiency == DataSufficiencyStatus.SUFFICIENT else None,
            trajectory_direction="increasing" if data_sufficiency == DataSufficiencyStatus.SUFFICIENT else "insufficient_history",
            annualized_rate=hba1c_rate if data_sufficiency == DataSufficiencyStatus.SUFFICIENT else None,
        ),
        source_features_used=["hba1c_latest", "hba1c_previous", "hba1c_change", "hba1c_annualized_rate"]
        if data_sufficiency == DataSufficiencyStatus.SUFFICIENT
        else ["hba1c_latest"],
        unavailable_inputs=[]
        if data_sufficiency == DataSufficiencyStatus.SUFFICIENT
        else ["hba1c_previous", "hba1c_change", "hba1c_annualized_rate"],
        documented_limitations=["Estimator in foundation phase (v0.1.0-foundation)."],
        is_diagnostic_claim=False,
        treatment_recommendations_allowed=False,
        non_diagnostic_disclaimer="Factual clinical explanation context for decision support only. Strictly non-diagnostic.",
    )


def test_1_prompt_contains_only_approved_explanation_context_information():
    context = create_mock_explanation_context()
    system_inst, user_prompt = build_diabetes_narrative_prompt(context)

    # System instruction enforces safety rules
    assert "USE ONLY VERIFIED FACTS" in system_inst
    assert "NO TREATMENT RECOMMENDATIONS" in system_inst
    assert "CALIBRATION SAFETY" in system_inst
    assert "OUTPUT FORMAT" in system_inst

    # User prompt contains verified metrics
    assert "PT-NARR-TEST-01" in user_prompt
    assert "8.2" in user_prompt
    assert "7.6" in user_prompt
    assert "0.6" in user_prompt
    assert "0.86" in user_prompt
    assert "sufficient_data" in user_prompt
    assert "not_calibrated" in user_prompt


def test_2_raw_fhir_and_clinical_notes_not_passed_to_llm():
    context = create_mock_explanation_context()
    _, user_prompt = build_diabetes_narrative_prompt(context)

    # Asserts that raw FHIR bundle schemas and clinical progress notes do NOT leak into LLM prompt
    assert "resourceType" not in user_prompt
    assert "clinical_notes" not in user_prompt
    assert "coding" not in user_prompt
    assert "fullUrl" not in user_prompt
    assert "practitioner" not in user_prompt


def test_3_uncalibrated_risk_never_becomes_numerical_probability():
    context = create_mock_explanation_context(is_calibrated=False)

    # LLM output hallucinating a numerical probability must be rejected by validator
    fabricated_output = json.dumps({
        "summary": "Patient glycemic trajectory is rising.",
        "observed_trajectory": "HbA1c increased from 7.6% to 8.2%.",
        "data_limitations": "3 measurements over 253 days.",
        "statistical_calibration_status": "Patient has an estimated 42% risk of microvascular complications.",
        "disclaimer": "Non-diagnostic decision support.",
    })

    with pytest.raises(ClinicalNarrativeValidationError, match="unauthorized numerical probability"):
        narrative_service.validate_and_parse_llm_payload(fabricated_output, context=context)


def test_4_missing_hba1c_history_represented_correctly():
    context_single = create_mock_explanation_context(
        data_sufficiency=DataSufficiencyStatus.INSUFFICIENT, count=1
    )
    _, user_prompt = build_diabetes_narrative_prompt(context_single)

    assert '"is_available": false' in user_prompt
    assert "hba1c_previous" in user_prompt
    assert "insufficient_history" in user_prompt


@pytest.mark.asyncio
async def test_5_structured_llm_output_validated():
    context = create_mock_explanation_context()
    provider = MockLLMProvider()

    system_inst, user_prompt = build_diabetes_narrative_prompt(context)
    raw_output = await provider.generate_structured_narrative(system_inst, user_prompt)

    payload = narrative_service.validate_and_parse_llm_payload(raw_output, context=context)

    assert payload.summary != ""
    assert "8.2" in payload.observed_trajectory
    assert "not calibrated" in payload.statistical_calibration_status.lower()
    assert payload.data_limitations != ""
    assert "non-diagnostic" in payload.disclaimer.lower()


def test_6_malformed_llm_output_rejected_safely():
    context = create_mock_explanation_context()

    # Case A: Invalid JSON text
    with pytest.raises(ClinicalNarrativeValidationError, match="valid JSON"):
        narrative_service.validate_and_parse_llm_payload("This is plain conversational text without JSON.", context=context)

    # Case B: Missing required schema fields
    incomplete_json = json.dumps({"summary": "Incomplete payload missing other 4 fields"})
    with pytest.raises(ClinicalNarrativeValidationError, match="structured schema"):
        narrative_service.validate_and_parse_llm_payload(incomplete_json, context=context)


def test_7_treatment_recommendations_rejected_or_prevented():
    context = create_mock_explanation_context()

    # Attempting to return medication directives must trigger ClinicalNarrativeValidationError
    directive_output = json.dumps({
        "summary": "Prescribe metformin 500mg twice daily immediately to lower glucose levels.",
        "observed_trajectory": "HbA1c increased to 8.2%.",
        "data_limitations": "3 measurements.",
        "statistical_calibration_status": "Not calibrated.",
        "disclaimer": "Non-diagnostic decision support.",
    })

    with pytest.raises(ClinicalNarrativeValidationError, match="prescription or treatment directives"):
        narrative_service.validate_and_parse_llm_payload(directive_output, context=context)


def test_8_input_explanation_context_remains_unchanged():
    context = create_mock_explanation_context()
    context_copy = copy.deepcopy(context)

    build_diabetes_narrative_prompt(context)

    assert context == context_copy


def test_9_provider_configuration_errors_handled_safely():
    # Attempting to load unconfigured provider raises ProviderNotConfiguredError
    with pytest.raises(ProviderNotConfiguredError, match="GENAI_API_KEY is not configured"):
        get_llm_provider("gemini", api_key_override=None)

    with pytest.raises(ProviderNotConfiguredError, match="Unsupported or unrecognized"):
        get_llm_provider("unsupported_cloud_vendor")


@pytest.mark.asyncio
async def test_10_audit_traceability_preserved_on_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ingest standard patient record
        sample_res = await ac.get("/api/v1/emr/sample-fhir")
        ingest_res = await ac.post("/api/v1/emr/ingest", json=sample_res.json())
        assert ingest_res.status_code == 201
        patient_id = ingest_res.json()["patient_record"]["patient_id"]

        # Call POST narrative endpoint
        narrative_res = await ac.post(
            f"/api/v1/genai/narrative/patients/{patient_id}/diabetes",
            headers={"X-Actor-ID": "dr-endocrinologist-88"},
        )
        assert narrative_res.status_code == 200
        data = narrative_res.json()

        # Check response structure
        assert data["patient_id"] == patient_id
        assert data["domain"] == "diabetes"
        assert data["narrative_id"].startswith("narr-dm-")
        assert data["context_id"].startswith("ctx-dm-")
        assert "summary" in data
        assert "observed_trajectory" in data
        assert "data_limitations" in data
        assert "statistical_calibration_status" in data
        assert "disclaimer" in data
        assert data["provider"] == "mock"

        # Check HIPAA audit trail
        events = audit_service.get_recent_events()
        matching = [
            e for e in events
            if e.action == "generate_diabetes_narrative"
            and e.resource_id == patient_id
            and e.actor_id == "dr-endocrinologist-88"
        ]
        assert len(matching) >= 1
        latest_event = matching[-1]
        assert latest_event.status == "success"
        assert latest_event.metadata["narrative_id"] == data["narrative_id"]
        assert latest_event.metadata["context_id"] == data["context_id"]
        assert latest_event.metadata["provider"] == "mock"
