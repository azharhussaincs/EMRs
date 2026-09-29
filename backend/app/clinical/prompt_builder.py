import json
from typing import Tuple
from app.schemas.explanation import AIExplanationContext, ASCVDExplanationContext


SYSTEM_INSTRUCTION_TEMPLATE = """You are a clinical decision support narrative synthesizer.
Your responsibility is to produce a strictly factual, structured clinical explanation of the patient's glycemic trajectory for review by a licensed clinician.

CRITICAL CLINICAL & STATISTICAL SAFETY RULES:
1. USE ONLY VERIFIED FACTS: Use only the measurements, timestamps, and limitations provided in the clinical context JSON below.
2. DO NOT INVENT FACTS: Never hallucinate, estimate, or assume missing clinical observations, vital signs, or lab values.
3. PRESERVE VALUES & DATES: Exact numerical values (e.g. latest HbA1c, baseline HbA1c, rate of change) and source dates must be preserved exactly as supplied.
4. NO TREATMENT RECOMMENDATIONS: You must NOT recommend, adjust, suggest, or direct any medications, prescriptions, therapies, or clinical interventions.
5. NO AUTONOMOUS DIAGNOSIS: Do not diagnose the patient with a condition. Clearly distinguish observed trajectory measurements from clinical interpretation.
6. CALIBRATION SAFETY: The current estimator is NOT CALIBRATED. You must NOT invent, estimate, or emit any numerical risk percentage, probability (0-100%), or confidence interval. Explicitly state that the estimator is uncalibrated and numerical probability is withheld.
7. INSUFFICIENT DATA TRANSPARENCY: If measurements are missing or insufficient (e.g. single observation), explicitly state that longitudinal trajectory cannot be confirmed.
8. REGULATORY DISCLAIMER: You must include the provided non-diagnostic decision boundary disclaimer.

OUTPUT FORMAT:
You must output a single, valid JSON object containing exactly these five string fields:
{
  "summary": "<High-level factual clinical synthesis of the observed glycemic trajectory>",
  "observed_trajectory": "<Chronological detail of HbA1c measurements, baseline comparison, absolute delta, and annualized velocity>",
  "data_limitations": "<Documented limitations, measurement count, interval, and unavailable inputs>",
  "statistical_calibration_status": "<Explicit statement that estimator is uncalibrated and no numerical probability is emitted>",
  "disclaimer": "<Mandatory regulatory non-diagnostic disclaimer exactly as provided>"
}
Do not wrap your response in conversational text. Return only valid JSON.
"""


CARDIOVASCULAR_SYSTEM_INSTRUCTION_TEMPLATE = """You are a clinical decision support narrative synthesizer.
Your responsibility is to produce a strictly factual, structured clinical explanation of the patient's cardiovascular (ASCVD) clinical risk factors and blood pressure trajectory for review by a licensed clinician.

CRITICAL CLINICAL & STATISTICAL SAFETY RULES:
1. USE ONLY VERIFIED FACTS: Use only the measurements, timestamps, risk factors, and limitations provided in the clinical context JSON below.
2. DO NOT INVENT FACTS: Never hallucinate, estimate, or assume missing clinical observations, vital signs, lipid levels, or smoking status.
3. PRESERVE VALUES & DATES: Exact numerical values (e.g. resting systolic BP, total cholesterol, HDL, BP mean) and source dates must be preserved exactly as supplied.
4. NO TREATMENT OR MEDICATION DIRECTIVES: You must NOT recommend, adjust, suggest, or direct any medications, prescriptions, statin therapy, antihypertensive therapy, or clinical interventions.
5. NO AUTONOMOUS DIAGNOSIS: Do not diagnose the patient with a condition (e.g. hypertension, hyperlipidemia, ASCVD). Clearly distinguish observed risk factors from clinical interpretation.
6. CALIBRATION SAFETY: The current estimator is in foundation status and is NOT CALIBRATED. You must NOT invent, estimate, or emit any numerical ASCVD risk percentage, probability (0-100%), or 10-year risk score. Explicitly state that the estimator is uncalibrated and numerical probability is withheld.
7. INSUFFICIENT DATA TRANSPARENCY: If clinical risk parameters are missing or unavailable (e.g. missing lipid panel, undocumented smoking status), explicitly state that complete ASCVD profile cannot be confirmed.
8. REGULATORY DISCLAIMER: You must include the provided non-diagnostic decision boundary disclaimer.

OUTPUT FORMAT:
You must output a single, valid JSON object containing exactly these five string fields:
{
  "summary": "<High-level factual clinical synthesis of the observed cardiovascular risk profile>",
  "observed_trajectory": "<Chronological detail of blood pressure readings, lipid biomarker levels, age, sex, smoking status, and diabetes history>",
  "data_limitations": "<Documented limitations, missing inputs, and data sufficiency status>",
  "statistical_calibration_status": "<Explicit statement that estimator is uncalibrated against population cohorts and no numerical probability is emitted>",
  "disclaimer": "<Mandatory regulatory non-diagnostic disclaimer exactly as provided>"
}
Do not wrap your response in conversational text. Return only valid JSON.
"""


def build_diabetes_narrative_prompt(
    context: AIExplanationContext,
) -> Tuple[str, str]:
    """
    Constructs controlled system instructions and grounded user prompt
    strictly from the verified AIExplanationContext.

    Guarantees:
    - Pure function; zero mutations of input context.
    - No raw FHIR bundle, clinical notes, or unnecessary PHI is passed.
    - Grounded exclusively in verified trajectory facts.
    """
    # Build clean, minimal factual dictionary for prompt payload
    factual_payload = {
        "patient_reference": context.patient_id,
        "assessment_id": context.assessment_id,
        "clinical_domain": context.domain.value,
        "data_sufficiency": context.data_sufficiency.value,
        "calibration_status": context.calibration_status.value,
        "calibrated_risk_score": None,  # Explicitly None to prevent probability fabrication
        "latest_hba1c": {
            "is_available": context.latest_hba1c.is_available,
            "value": context.latest_hba1c.value,
            "unit": context.latest_hba1c.unit,
            "source_timestamp": context.latest_hba1c.source_timestamp.isoformat()
            if context.latest_hba1c.source_timestamp
            else None,
        },
        "previous_hba1c": {
            "is_available": context.previous_hba1c.is_available,
            "value": context.previous_hba1c.value,
            "unit": context.previous_hba1c.unit,
            "source_timestamp": context.previous_hba1c.source_timestamp.isoformat()
            if context.previous_hba1c.source_timestamp
            else None,
        },
        "absolute_change": {
            "is_available": context.absolute_change.is_available,
            "value": context.absolute_change.value,
            "unit": context.absolute_change.unit,
        },
        "annualized_rate": {
            "is_available": context.annualized_rate.is_available,
            "value": context.annualized_rate.value,
            "unit": context.annualized_rate.unit,
        },
        "trajectory_summary": {
            "measurement_count": context.trajectory_summary.measurement_count,
            "time_interval_days": context.trajectory_summary.time_interval_days,
            "trajectory_direction": context.trajectory_summary.trajectory_direction,
        },
        "unavailable_inputs": context.unavailable_inputs,
        "documented_limitations": context.documented_limitations,
        "non_diagnostic_disclaimer": context.non_diagnostic_disclaimer,
    }

    user_prompt = (
        f"Verified Clinical Explanation Context:\n"
        f"```json\n{json.dumps(factual_payload, indent=2)}\n```\n\n"
        f"Synthesize the structured factual clinical explanation JSON strictly conforming to the system instructions."
    )

    return SYSTEM_INSTRUCTION_TEMPLATE.strip(), user_prompt


def build_cardiovascular_narrative_prompt(
    context: ASCVDExplanationContext,
) -> Tuple[str, str]:
    """
    Constructs controlled system instructions and grounded user prompt
    strictly from the verified ASCVDExplanationContext.

    Guarantees:
    - Pure function; zero mutations of input context.
    - No raw FHIR bundle, clinical notes, or unnecessary PHI is passed.
    - Grounded exclusively in verified ASCVD risk factor facts.
    """
    factual_payload = {
        "patient_reference": context.patient_id,
        "assessment_id": context.assessment_id,
        "clinical_domain": context.domain.value,
        "data_sufficiency": context.data_sufficiency.value,
        "calibration_status": context.calibration_status.value,
        "calibrated_risk_score": None,  # Explicitly None to prevent probability fabrication
        "age_years": context.age_years if context.age_available else None,
        "gender": context.gender if context.gender_available else None,
        "systolic_bp": {
            "is_available": context.systolic_bp.is_available,
            "value": context.systolic_bp.value,
            "unit": context.systolic_bp.unit,
            "source_timestamp": context.systolic_bp.source_timestamp.isoformat()
            if context.systolic_bp.source_timestamp
            else None,
            "mean": context.systolic_bp_mean,
            "standard_deviation": context.systolic_bp_std,
            "reading_count": context.systolic_bp_count,
        },
        "total_cholesterol": {
            "is_available": context.total_cholesterol.is_available,
            "value": context.total_cholesterol.value,
            "unit": context.total_cholesterol.unit,
            "source_timestamp": context.total_cholesterol.source_timestamp.isoformat()
            if context.total_cholesterol.source_timestamp
            else None,
        },
        "hdl_cholesterol": {
            "is_available": context.hdl_cholesterol.is_available,
            "value": context.hdl_cholesterol.value,
            "unit": context.hdl_cholesterol.unit,
            "source_timestamp": context.hdl_cholesterol.source_timestamp.isoformat()
            if context.hdl_cholesterol.source_timestamp
            else None,
        },
        "smoking_status": {
            "is_available": context.smoking_status_available,
            "value": context.smoking_status,
        },
        "diabetes_history": {
            "is_available": context.diabetes_status_available,
            "has_diabetes": context.has_diabetes,
        },
        "source_features_used": context.source_features_used,
        "unavailable_inputs": context.unavailable_inputs,
        "documented_limitations": context.documented_limitations,
        "non_diagnostic_disclaimer": context.non_diagnostic_disclaimer,
    }

    user_prompt = (
        f"Verified Clinical Explanation Context:\n"
        f"```json\n{json.dumps(factual_payload, indent=2)}\n```\n\n"
        f"Synthesize the structured factual clinical explanation JSON strictly conforming to the system instructions."
    )

    return CARDIOVASCULAR_SYSTEM_INSTRUCTION_TEMPLATE.strip(), user_prompt

