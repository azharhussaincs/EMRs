import json
import re
from app.clinical.providers.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic, offline clinical narrative provider for testing and validation.
    Synthesizes perfectly grounded JSON strictly from the verified payload in user_prompt.
    Guarantees:
    - Never fabricates probabilities.
    - Never generates treatment or prescription recommendations.
    - Explicitly marks uncalibrated state.
    """

    def __init__(self, model_name: str = "mock-clinical-synthesizer-v1"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_structured_narrative(
        self, system_instruction: str, user_prompt: str
    ) -> str:
        # Extract the JSON payload block from user_prompt
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", user_prompt)
        if not json_match:
            # Fallback if no code block
            raw_payload = {}
        else:
            try:
                raw_payload = json.loads(json_match.group(1))
            except Exception:
                raw_payload = {}

        domain = raw_payload.get("clinical_domain", "diabetes")
        if domain == "cardiovascular":
            patient_ref = raw_payload.get("patient_reference", "patient")
            data_sufficiency = raw_payload.get("data_sufficiency", "unavailable_feature")
            age = raw_payload.get("age_years")
            gender = raw_payload.get("gender")
            sbp = raw_payload.get("systolic_bp", {})
            tc = raw_payload.get("total_cholesterol", {})
            hdl = raw_payload.get("hdl_cholesterol", {})
            smoking = raw_payload.get("smoking_status", {})
            diabetes = raw_payload.get("diabetes_history", {})
            limitations = raw_payload.get("documented_limitations", [])
            disclaimer = raw_payload.get(
                "non_diagnostic_disclaimer",
                "Factual clinical explanation context for decision support only. Strictly non-diagnostic and non-prescriptive. Treatment directives and statin therapy recommendations prohibited.",
            )

            if data_sufficiency == "sufficient_data":
                sbp_val = sbp.get("value")
                sbp_mean = sbp.get("mean")
                sbp_unit = sbp.get("unit", "mmHg")
                sbp_count = sbp.get("reading_count", 1)
                tc_val = tc.get("value")
                tc_unit = tc.get("unit", "mg/dL")
                hdl_val = hdl.get("value")
                hdl_unit = hdl.get("unit", "mg/dL")
                smoke_val = smoking.get("value")
                dm_val = "confirmed present" if diabetes.get("has_diabetes") else "absent/not documented"

                summary = (
                    f"Cardiovascular risk factor assessment for {patient_ref} ({age}-year-old {gender}) "
                    f"documents resting systolic blood pressure of {sbp_val} {sbp_unit}, total cholesterol of "
                    f"{tc_val} {tc_unit}, HDL cholesterol of {hdl_val} {hdl_unit}, smoking status '{smoke_val}', "
                    f"and diabetes {dm_val}."
                )
                observed_trajectory = (
                    f"Blood pressure profile includes {sbp_count} systolic readings with a mean of {sbp_mean} {sbp_unit} "
                    f"and latest reading of {sbp_val} {sbp_unit}. Lipid biomarkers indicate total cholesterol {tc_val} {tc_unit} "
                    f"and HDL {hdl_val} {hdl_unit}. Documented smoking status is {smoke_val}."
                )
                data_limitations = (
                    f"All 7 required ASCVD risk parameters are present in record without imputation. Documented constraints: "
                    f"{'; '.join(limitations) if limitations else 'Foundation research estimator phase.'}"
                )
                calibration_status = (
                    "The cardiovascular risk estimator is in uncalibrated foundation phase (v0.1.0-foundation). "
                    "In accordance with clinical safety principles, numerical ASCVD risk probability and 10-year percentages are strictly withheld."
                )
            elif data_sufficiency == "insufficient_data":
                missing = raw_payload.get("unavailable_inputs", [])
                summary = (
                    f"Partial cardiovascular risk factor profile documented for {patient_ref}. "
                    f"Complete ASCVD risk evaluation is hindered by missing clinical inputs: {', '.join(missing)}."
                )
                observed_trajectory = (
                    f"Available parameters include systolic BP {sbp.get('value')} {sbp.get('unit', 'mmHg')} "
                    f"and total cholesterol {tc.get('value')} {tc.get('unit', 'mg/dL')}. Missing required inputs: {', '.join(missing)}."
                )
                data_limitations = (
                    f"Incomplete ASCVD risk factor profile ({len(missing)} required inputs missing). "
                    f"Missing values are preserved without statistical imputation."
                )
                calibration_status = (
                    "Estimator is uncalibrated and data sufficiency is incomplete. Numerical risk probability is strictly withheld."
                )
            else:
                summary = (
                    f"No cardiovascular or lipid observations found in the medical record for {patient_ref}."
                )
                observed_trajectory = (
                    "Cardiovascular and lipid biomarkers are unavailable. No ASCVD risk profile can be derived."
                )
                data_limitations = (
                    f"Missing required cardiovascular biomarkers: {', '.join(raw_payload.get('unavailable_inputs', []))}."
                )
                calibration_status = (
                    "Features unavailable; estimator cannot evaluate cardiovascular risk. Numerical probability is not calculated."
                )

            payload = {
                "summary": summary,
                "observed_trajectory": observed_trajectory,
                "data_limitations": data_limitations,
                "statistical_calibration_status": calibration_status,
                "disclaimer": disclaimer,
            }
            return json.dumps(payload, indent=2)

        patient_ref = raw_payload.get("patient_reference", "patient")
        data_sufficiency = raw_payload.get("data_sufficiency", "unavailable_feature")
        latest = raw_payload.get("latest_hba1c", {})
        prev = raw_payload.get("previous_hba1c", {})
        change = raw_payload.get("absolute_change", {})
        rate = raw_payload.get("annualized_rate", {})
        traj = raw_payload.get("trajectory_summary", {})
        disclaimer = raw_payload.get(
            "non_diagnostic_disclaimer",
            "Factual clinical explanation context for decision support only. Strictly non-diagnostic and non-prescriptive.",
        )
        limitations = raw_payload.get("documented_limitations", [])

        # Formulate grounded sections based on factual sufficiency
        if data_sufficiency == "sufficient_data":
            latest_val = latest.get("value")
            latest_unit = latest.get("unit", "%")
            prev_val = prev.get("value")
            prev_unit = prev.get("unit", "%")
            chg_val = change.get("value")
            rate_val = rate.get("value")
            count = traj.get("measurement_count", 2)
            days = traj.get("time_interval_days", 0)

            summary = (
                f"Longitudinal glycemic review for {patient_ref} indicates an observed HbA1c increase "
                f"from baseline {prev_val} {prev_unit} to {latest_val} {latest_unit}."
            )
            observed_trajectory = (
                f"Record documents {count} sequential HbA1c observations over an interval of {days:.1f} days. "
                f"The latest measurement is {latest_val} {latest_unit} (previous: {prev_val} {prev_unit}), "
                f"reflecting an absolute change of +{chg_val} {latest_unit} and an annualized progression velocity of +{rate_val} %/year."
            )
            data_limitations = (
                f"Trajectory is derived from {count} temporal measurements. Documented constraints: "
                f"{'; '.join(limitations) if limitations else 'No additional limitations.'}"
            )
            calibration_status = (
                "The underlying risk estimator is in foundation status (not calibrated against longitudinal cohorts). "
                "In accordance with clinical safety principles, no numerical risk probability or percentage is emitted."
            )
        elif data_sufficiency == "insufficient_data":
            latest_val = latest.get("value")
            latest_unit = latest.get("unit", "%")
            summary = (
                f"Isolated static HbA1c measurement of {latest_val} {latest_unit} recorded for {patient_ref}. "
                f"Longitudinal trajectory cannot be confirmed due to insufficient historical measurements."
            )
            observed_trajectory = (
                f"A single HbA1c observation of {latest_val} {latest_unit} is documented. Preceding baseline values, "
                f"absolute change, and annualized rate of change are unavailable."
            )
            data_limitations = (
                f"Insufficient historical data: {'; '.join(limitations) if limitations else 'At least 2 historical observations required.'}"
            )
            calibration_status = (
                "Estimator is uncalibrated and data history is insufficient. Numerical risk probability is strictly withheld."
            )
        else:
            summary = (
                f"No glycated hemoglobin (HbA1c) observations were identified in the medical record for {patient_ref}."
            )
            observed_trajectory = (
                "HbA1c laboratory observations are unavailable. No chronological trajectory can be derived."
            )
            data_limitations = (
                f"Missing required domain biomarkers: {', '.join(raw_payload.get('unavailable_inputs', []))}."
            )
            calibration_status = (
                "Feature unavailable; model cannot evaluate trajectory. Numerical probability is not calculated."
            )

        payload = {
            "summary": summary,
            "observed_trajectory": observed_trajectory,
            "data_limitations": data_limitations,
            "statistical_calibration_status": calibration_status,
            "disclaimer": disclaimer,
        }

        return json.dumps(payload, indent=2)
