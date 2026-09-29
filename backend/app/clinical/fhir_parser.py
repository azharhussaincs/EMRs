import re
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from app.clinical.constraints import (
    CLINICAL_CONSTRAINTS,
    LOINC_TO_BIOMARKER_KEY,
    BiomarkerClinicalConstraint,
)
from app.schemas.emr import (
    ClinicalCoding,
    ClinicalValidationErrorItem,
    EMRObservation,
    EMRCondition,
    EMRMedication,
    EMRClinicalNote,
    PatientEMRPayload,
    NormalizedBiomarkerPoint,
    NormalizedCondition,
    NormalizedMedication,
    NormalizedClinicalNote,
    NormalizedPatientRecord,
)


class FHIRClinicalParser:
    """
    Production-grade parser and normalizer for HL7 FHIR R4 Bundles and de-identified EMR payloads.
    Enforces clinical plausibility constraints and chronological longitudinal sequences.
    """

    @classmethod
    def parse_raw_payload(cls, raw: Dict[str, Any]) -> Tuple[PatientEMRPayload, List[ClinicalValidationErrorItem]]:
        """
        Parses either a FHIR R4 Bundle or a direct PatientEMRPayload JSON structure.
        """
        errors: List[ClinicalValidationErrorItem] = []

        # Check if payload is a standard FHIR R4 Bundle
        if raw.get("resourceType") == "Bundle":
            return cls._parse_fhir_bundle(raw)

        # Otherwise validate as direct PatientEMRPayload
        try:
            payload = PatientEMRPayload(**raw)
            return payload, []
        except Exception as e:
            errors.append(
                ClinicalValidationErrorItem(
                    field="payload",
                    issue=f"Failed to parse payload structure: {str(e)}",
                    code="PAYLOAD_SCHEMA_INVALID",
                )
            )
            return PatientEMRPayload(patient_id="UNKNOWN"), errors

    @classmethod
    def _parse_fhir_bundle(cls, bundle: Dict[str, Any]) -> Tuple[PatientEMRPayload, List[ClinicalValidationErrorItem]]:
        errors: List[ClinicalValidationErrorItem] = []
        entries = bundle.get("entry", [])
        if not isinstance(entries, list):
            errors.append(
                ClinicalValidationErrorItem(
                    field="entry",
                    issue="FHIR Bundle 'entry' property must be a list of resource wrappers.",
                    code="FHIR_BUNDLE_MALFORMED",
                )
            )
            return PatientEMRPayload(patient_id="UNKNOWN"), errors

        patient_id = None
        birth_date = None
        gender = None
        observations: List[EMRObservation] = []
        conditions: List[EMRCondition] = []
        medications: List[EMRMedication] = []
        clinical_notes: List[EMRClinicalNote] = []

        for idx, wrapper in enumerate(entries):
            res = wrapper.get("resource")
            if not isinstance(res, dict):
                continue

            r_type = res.get("resourceType")

            # 1. Patient Resource
            if r_type == "Patient":
                patient_id = res.get("id") or patient_id
                gender = res.get("gender")
                b_date_str = res.get("birthDate")
                if b_date_str:
                    try:
                        birth_date = date.fromisoformat(b_date_str[:10])
                    except ValueError:
                        errors.append(
                            ClinicalValidationErrorItem(
                                field=f"entry[{idx}].resource.birthDate",
                                issue=f"Invalid ISO birthDate string: '{b_date_str}'",
                                code="INVALID_DATE_FORMAT",
                                observed_value=b_date_str,
                            )
                        )

            # 2. Observation Resource
            elif r_type == "Observation":
                parsed_obs, obs_errs = cls._parse_fhir_observation(res, idx)
                observations.extend(parsed_obs)
                errors.extend(obs_errs)

            # 3. Condition Resource
            elif r_type == "Condition":
                parsed_cond, cond_errs = cls._parse_fhir_condition(res, idx)
                if parsed_cond:
                    conditions.append(parsed_cond)
                errors.extend(cond_errs)

            # 4. MedicationRequest or MedicationStatement
            elif r_type in ("MedicationRequest", "MedicationStatement"):
                parsed_med, med_errs = cls._parse_fhir_medication(res, idx)
                if parsed_med:
                    medications.append(parsed_med)
                errors.extend(med_errs)

            # 5. DocumentReference (Clinical Notes)
            elif r_type == "DocumentReference":
                parsed_note, note_errs = cls._parse_fhir_document(res, idx)
                if parsed_note:
                    clinical_notes.append(parsed_note)
                errors.extend(note_errs)

        if not patient_id:
            # Fallback to subject reference if available
            for obs in observations:
                if getattr(obs, "patient_id", None):
                    patient_id = obs.patient_id
                    break
            if not patient_id:
                patient_id = "ANONYMOUS-PATIENT"

        payload = PatientEMRPayload(
            patient_id=str(patient_id),
            birth_date=birth_date,
            gender=gender,
            observations=observations,
            conditions=conditions,
            medications=medications,
            clinical_notes=clinical_notes,
            metadata={"source_format": "FHIR_R4_BUNDLE", "entries_count": len(entries)},
        )
        return payload, errors

    @classmethod
    def _parse_fhir_observation(
        cls, res: Dict[str, Any], idx: int
    ) -> Tuple[List[EMRObservation], List[ClinicalValidationErrorItem]]:
        results: List[EMRObservation] = []
        errors: List[ClinicalValidationErrorItem] = []

        obs_id = res.get("id", f"obs-{idx}")
        code_obj = res.get("code", {})
        codings = code_obj.get("coding", [])

        primary_code = "UNKNOWN"
        primary_system = "http://loinc.org"
        primary_display = code_obj.get("text")

        if codings and isinstance(codings, list):
            first = codings[0]
            primary_code = str(first.get("code", "UNKNOWN"))
            primary_system = first.get("system", primary_system)
            primary_display = first.get("display", primary_display)

        # Timestamp
        date_str = res.get("effectiveDateTime") or res.get("issued")
        if not date_str:
            errors.append(
                ClinicalValidationErrorItem(
                    field=f"entry[{idx}].Observation.effectiveDateTime",
                    issue="Observation requires effectiveDateTime or issued timestamp to preserve longitudinal clinical history.",
                    code="MISSING_OBSERVATION_TIMESTAMP",
                )
            )
            return results, errors

        try:
            effective_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            errors.append(
                ClinicalValidationErrorItem(
                    field=f"entry[{idx}].Observation.effectiveDateTime",
                    issue=f"Invalid ISO datetime string: '{date_str}'",
                    code="INVALID_DATETIME_FORMAT",
                    observed_value=date_str,
                )
            )
            return results, errors

        # Check for multi-component observation (e.g. Blood Pressure Panel LOINC 85354-9)
        components = res.get("component")
        if components and isinstance(components, list):
            for c_idx, comp in enumerate(components):
                c_code_obj = comp.get("code", {})
                c_codings = c_code_obj.get("coding", [])
                c_code = "UNKNOWN"
                c_display = c_code_obj.get("text")
                if c_codings:
                    c_code = str(c_codings[0].get("code", "UNKNOWN"))
                    c_display = c_codings[0].get("display", c_display)

                val_qty = comp.get("valueQuantity", {})
                num_val = val_qty.get("value")
                unit_val = val_qty.get("unit") or val_qty.get("code")

                if num_val is not None:
                    results.append(
                        EMRObservation(
                            observation_id=f"{obs_id}-comp-{c_idx}",
                            code=ClinicalCoding(system="http://loinc.org", code=c_code, display=c_display),
                            effective_datetime=effective_dt,
                            value_numeric=float(num_val),
                            unit=unit_val,
                        )
                    )
            return results, errors

        # Single value observation
        val_qty = res.get("valueQuantity", {})
        num_val = val_qty.get("value")
        unit_val = val_qty.get("unit") or val_qty.get("code")
        str_val = res.get("valueString")

        ref_ranges = res.get("referenceRange", [])
        ref_low = None
        ref_high = None
        if ref_ranges and isinstance(ref_ranges, list):
            low_obj = ref_ranges[0].get("low", {})
            high_obj = ref_ranges[0].get("high", {})
            ref_low = low_obj.get("value")
            ref_high = high_obj.get("value")

        results.append(
            EMRObservation(
                observation_id=str(obs_id),
                code=ClinicalCoding(system=primary_system, code=primary_code, display=primary_display),
                effective_datetime=effective_dt,
                value_numeric=float(num_val) if num_val is not None else None,
                value_string=str_val,
                unit=unit_val,
                reference_range_low=float(ref_low) if ref_low is not None else None,
                reference_range_high=float(ref_high) if ref_high is not None else None,
            )
        )
        return results, errors

    @classmethod
    def _parse_fhir_condition(
        cls, res: Dict[str, Any], idx: int
    ) -> Tuple[Optional[EMRCondition], List[ClinicalValidationErrorItem]]:
        cond_id = res.get("id", f"cond-{idx}")
        code_obj = res.get("code", {})
        codings = code_obj.get("coding", [])
        primary_code = "UNKNOWN"
        primary_system = "http://hl7.org/fhir/sid/icd-10"
        primary_display = code_obj.get("text", "Clinical Condition")

        if codings and isinstance(codings, list):
            primary_code = str(codings[0].get("code", "UNKNOWN"))
            primary_system = codings[0].get("system", primary_system)
            primary_display = codings[0].get("display", primary_display)

        rec_date_str = res.get("recordedDate") or res.get("onsetDateTime")
        rec_date = None
        if rec_date_str:
            try:
                rec_date = date.fromisoformat(rec_date_str[:10])
            except ValueError:
                pass

        clin_status = "active"
        cs_obj = res.get("clinicalStatus", {})
        if isinstance(cs_obj, dict) and cs_obj.get("coding"):
            clin_status = cs_obj["coding"][0].get("code", "active")

        return (
            EMRCondition(
                condition_id=str(cond_id),
                code=ClinicalCoding(system=primary_system, code=primary_code, display=primary_display),
                clinical_status=str(clin_status),
                recorded_date=rec_date,
            ),
            [],
        )

    @classmethod
    def _parse_fhir_medication(
        cls, res: Dict[str, Any], idx: int
    ) -> Tuple[Optional[EMRMedication], List[ClinicalValidationErrorItem]]:
        med_id = res.get("id", f"med-{idx}")
        med_cc = res.get("medicationCodeableConcept", {})
        codings = med_cc.get("coding", [])
        display_name = med_cc.get("text") or "Pharmacotherapy Agent"
        rxnorm_code = None

        if codings and isinstance(codings, list):
            first = codings[0]
            display_name = first.get("display", display_name)
            rxnorm_code = str(first.get("code", ""))

        dosage_instruction = None
        dosages = res.get("dosageInstruction", [])
        if dosages and isinstance(dosages, list):
            dosage_instruction = dosages[0].get("text")

        status_val = res.get("status", "active")

        return (
            EMRMedication(
                medication_id=str(med_id),
                code=ClinicalCoding(system="http://www.nlm.nih.gov/research/umls/rxnorm", code=rxnorm_code or "NONE") if rxnorm_code else None,
                display_name=display_name,
                status=str(status_val),
                dosage_instruction=dosage_instruction,
            ),
            [],
        )

    @classmethod
    def _parse_fhir_document(
        cls, res: Dict[str, Any], idx: int
    ) -> Tuple[Optional[EMRClinicalNote], List[ClinicalValidationErrorItem]]:
        doc_id = res.get("id", f"note-{idx}")
        type_obj = res.get("type", {})
        note_type = type_obj.get("text") or "Clinical Consultation Note"

        created_str = res.get("date") or datetime.now(timezone.utc).isoformat()
        try:
            created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except ValueError:
            created_at = datetime.now(timezone.utc)

        # Extract text content
        content_list = res.get("content", [])
        text_content = ""
        if content_list and isinstance(content_list, list):
            att = content_list[0].get("attachment", {})
            text_content = att.get("data") or att.get("title") or "Clinical consultation details recorded."

        return (
            EMRClinicalNote(
                note_id=str(doc_id),
                note_type=note_type,
                created_at=created_at,
                sanitized_text=text_content,
            ),
            [],
        )


class ClinicalSemanticValidator:
    """
    Validates clinical plausibility, physiological limits, temporal consistency, and ontology integrity.
    Rejects malformed or biologically impossible values.
    """

    @classmethod
    def validate_and_normalize(
        cls, payload: PatientEMRPayload
    ) -> Tuple[Optional[NormalizedPatientRecord], List[ClinicalValidationErrorItem], List[str]]:
        errors: List[ClinicalValidationErrorItem] = []
        warnings: List[str] = []
        now_utc = datetime.now(timezone.utc)
        # Allow 24 hours future buffer for client timezone clock skew
        future_cutoff = now_utc + timedelta(days=1)

        # 1. Patient Demographics Validation
        if not payload.patient_id or payload.patient_id.strip() in ("", "UNKNOWN"):
            errors.append(
                ClinicalValidationErrorItem(
                    field="patient_id",
                    issue="Pseudonymous Patient ID is mandatory and cannot be empty.",
                    code="PATIENT_ID_MANDATORY",
                )
            )

        age_years: Optional[int] = None
        if payload.birth_date:
            if payload.birth_date > now_utc.date():
                errors.append(
                    ClinicalValidationErrorItem(
                        field="birth_date",
                        issue=f"Patient birth date ({payload.birth_date}) cannot be in the future.",
                        code="PHYSIOLOGICAL_FUTURE_BIRTH_DATE",
                        observed_value=str(payload.birth_date),
                    )
                )
            else:
                age_years = (now_utc.date() - payload.birth_date).days // 365
                if age_years > 130:
                    errors.append(
                        ClinicalValidationErrorItem(
                            field="birth_date",
                            issue=f"Calculated patient age ({age_years} years) exceeds plausible human lifespan (130 years).",
                            code="PHYSIOLOGICAL_AGE_EXCEEDED",
                            observed_value=age_years,
                        )
                    )

        # 2. Minimum clinical data presence check
        total_data_points = (
            len(payload.observations)
            + len(payload.conditions)
            + len(payload.medications)
            + len(payload.clinical_notes)
        )
        if total_data_points == 0:
            errors.append(
                ClinicalValidationErrorItem(
                    field="payload",
                    issue="EMR record contains zero clinical data points. At least one observation, condition, medication, or note is required.",
                    code="EMPTY_CLINICAL_RECORD",
                )
            )

        # 3. Clinical Observations Validation & Normalization
        longitudinal_biomarkers: Dict[str, List[NormalizedBiomarkerPoint]] = {}
        bp_systolic_map: Dict[str, float] = {}  # timestamp_str -> value
        bp_diastolic_map: Dict[str, float] = {} # timestamp_str -> value
        chol_total_map: Dict[str, float] = {}   # date_str -> value
        chol_hdl_map: Dict[str, float] = {}     # date_str -> value

        for idx, obs in enumerate(payload.observations):
            # Check timestamp
            if obs.effective_datetime > future_cutoff:
                errors.append(
                    ClinicalValidationErrorItem(
                        field=f"observations[{idx}].effective_datetime",
                        issue=f"Measurement timestamp ({obs.effective_datetime.isoformat()}) is in the future.",
                        code="FUTURE_TIMESTAMP_REJECTED",
                        observed_value=obs.effective_datetime.isoformat(),
                    )
                )

            # Check value presence
            if obs.value_numeric is None and not obs.value_string:
                errors.append(
                    ClinicalValidationErrorItem(
                        field=f"observations[{idx}]",
                        issue=f"Observation '{obs.observation_id}' contains neither numeric nor textual value.",
                        code="EMPTY_OBSERVATION_VALUE",
                    )
                )
                continue

            # Identify biomarker by LOINC code
            raw_code = obs.code.code.strip()
            biomarker_key = LOINC_TO_BIOMARKER_KEY.get(raw_code)

            # Physiological Range Check for numeric observations
            if obs.value_numeric is not None:
                val = obs.value_numeric

                if biomarker_key and biomarker_key in CLINICAL_CONSTRAINTS:
                    constraint = CLINICAL_CONSTRAINTS[biomarker_key]
                    if val < constraint.min_plausible or val > constraint.max_plausible:
                        errors.append(
                            ClinicalValidationErrorItem(
                                field=f"observations[{idx}].value_numeric",
                                issue=f"{constraint.standard_name} measurement {val} {constraint.standard_unit} violates physiological bounds ({constraint.min_plausible} - {constraint.max_plausible} {constraint.standard_unit}). {constraint.clinical_rationale}",
                                code="PHYSIOLOGICAL_RANGE_EXCEEDED",
                                observed_value=val,
                                acceptable_range=f"{constraint.min_plausible} - {constraint.max_plausible} {constraint.standard_unit}",
                            )
                        )
                    else:
                        # Collect for blood pressure cross-validation
                        time_key = obs.effective_datetime.isoformat()[:16]  # match within minute
                        date_key = obs.effective_datetime.isoformat()[:10]  # match within day
                        if biomarker_key == "systolic_bp":
                            bp_systolic_map[time_key] = val
                        elif biomarker_key == "diastolic_bp":
                            bp_diastolic_map[time_key] = val
                        elif biomarker_key == "total_cholesterol":
                            chol_total_map[date_key] = val
                        elif biomarker_key == "hdl_cholesterol":
                            chol_hdl_map[date_key] = val

                        # Add to normalized longitudinal collection
                        norm_pt = NormalizedBiomarkerPoint(
                            observation_id=obs.observation_id,
                            biomarker_key=biomarker_key,
                            standard_name=constraint.standard_name,
                            effective_datetime=obs.effective_datetime,
                            value=val,
                            unit=obs.unit or constraint.standard_unit,
                            loinc_code=raw_code,
                            reference_range_low=obs.reference_range_low,
                            reference_range_high=obs.reference_range_high,
                        )
                        longitudinal_biomarkers.setdefault(biomarker_key, []).append(norm_pt)
                else:
                    # General non-negative check for standard laboratory tests
                    if val < 0.0:
                        warnings.append(
                            f"Observation '{obs.code.display or raw_code}' reported negative value ({val}). Verified as atypical."
                        )

                    # Store as generic observation key
                    clean_key = f"obs_{re.sub(r'[^a-zA-Z0-9_]', '_', raw_code).lower()}"
                    norm_pt = NormalizedBiomarkerPoint(
                        observation_id=obs.observation_id,
                        biomarker_key=clean_key,
                        standard_name=obs.code.display or f"Lab {raw_code}",
                        effective_datetime=obs.effective_datetime,
                        value=val,
                        unit=obs.unit or "",
                        loinc_code=raw_code,
                        reference_range_low=obs.reference_range_low,
                        reference_range_high=obs.reference_range_high,
                    )
                    longitudinal_biomarkers.setdefault(clean_key, []).append(norm_pt)

        # 4. Blood Pressure Cross-Validation (Systolic vs Diastolic)
        for time_key, sys_val in bp_systolic_map.items():
            if time_key in bp_diastolic_map:
                dia_val = bp_diastolic_map[time_key]
                if sys_val <= dia_val:
                    errors.append(
                        ClinicalValidationErrorItem(
                            field="observations[blood_pressure]",
                            issue=f"Physiologically invalid blood pressure at {time_key}: Systolic ({sys_val} mmHg) must be strictly greater than Diastolic ({dia_val} mmHg).",
                            code="BLOOD_PRESSURE_INVERSION",
                            observed_value=f"{sys_val}/{dia_val} mmHg",
                        )
                    )

        # 4b. Lipid Panel Cross-Validation (Total Cholesterol vs HDL Fraction)
        for date_key, tot_val in chol_total_map.items():
            if date_key in chol_hdl_map:
                hdl_val = chol_hdl_map[date_key]
                if tot_val <= hdl_val:
                    errors.append(
                        ClinicalValidationErrorItem(
                            field="observations[lipid_panel]",
                            issue=f"Physiologically invalid lipid profile on {date_key}: Total Cholesterol ({tot_val} mg/dL) must be strictly greater than HDL Cholesterol fraction ({hdl_val} mg/dL).",
                            code="LIPID_FRACTION_INVERSION",
                            observed_value=f"Total: {tot_val}, HDL: {hdl_val} mg/dL",
                            acceptable_range=f"Total Cholesterol > HDL ({hdl_val} mg/dL)",
                        )
                    )

        # 5. Conditions Normalization
        normalized_conditions: List[NormalizedCondition] = []
        for idx, cond in enumerate(payload.conditions):
            raw_c_code = cond.code.code.strip()
            if not raw_c_code or raw_c_code == "UNKNOWN":
                errors.append(
                    ClinicalValidationErrorItem(
                        field=f"conditions[{idx}].code",
                        issue="Condition requires an ICD-10 or clinical concept code.",
                        code="MISSING_CONDITION_CODE",
                    )
                )
                continue

            normalized_conditions.append(
                NormalizedCondition(
                    condition_id=cond.condition_id,
                    icd10_code=raw_c_code,
                    display_name=cond.code.display or f"Diagnosis {raw_c_code}",
                    clinical_status=cond.clinical_status,
                    recorded_date=cond.recorded_date,
                )
            )

        # 6. Medications Normalization
        normalized_medications: List[NormalizedMedication] = []
        for med in payload.medications:
            normalized_medications.append(
                NormalizedMedication(
                    medication_id=med.medication_id,
                    display_name=med.display_name,
                    rxnorm_code=med.code.code if med.code else None,
                    dosage_instruction=med.dosage_instruction,
                    status=med.status,
                )
            )

        # 7. Clinical Notes Normalization
        normalized_notes: List[NormalizedClinicalNote] = []
        for note in payload.clinical_notes:
            preview = note.sanitized_text[:120] + ("..." if len(note.sanitized_text) > 120 else "")
            normalized_notes.append(
                NormalizedClinicalNote(
                    note_id=note.note_id,
                    note_type=note.note_type,
                    created_at=note.created_at,
                    author_specialty=note.author_specialty,
                    text_preview=preview,
                )
            )

        # If errors were accumulated, halt and return errors
        if errors:
            return None, errors, warnings

        # 8. Sort longitudinal biomarkers chronologically ascending
        all_timestamps: List[datetime] = []
        total_measurements = 0
        for b_key in longitudinal_biomarkers:
            longitudinal_biomarkers[b_key].sort(key=lambda pt: pt.effective_datetime)
            total_measurements += len(longitudinal_biomarkers[b_key])
            for pt in longitudinal_biomarkers[b_key]:
                all_timestamps.append(pt.effective_datetime)

        for n in normalized_notes:
            all_timestamps.append(n.created_at)

        earliest_date = min(all_timestamps) if all_timestamps else None
        latest_date = max(all_timestamps) if all_timestamps else None

        # 9. Evaluate 4-Domain Clinical Readiness
        has_diabetes_data = (
            "hba1c" in longitudinal_biomarkers
            or "fasting_glucose" in longitudinal_biomarkers
            or any(c.icd10_code.startswith("E11") or c.icd10_code.startswith("E10") for c in normalized_conditions)
        )
        has_cvd_data = (
            "systolic_bp" in longitudinal_biomarkers
            or "total_cholesterol" in longitudinal_biomarkers
            or any(c.icd10_code.startswith("I") for c in normalized_conditions)
        )
        has_ckd_data = (
            "egfr" in longitudinal_biomarkers
            or "serum_creatinine" in longitudinal_biomarkers
            or "urine_albumin_creatinine_ratio" in longitudinal_biomarkers
            or any(c.icd10_code.startswith("N18") for c in normalized_conditions)
        )
        has_cancer_data = (
            "cea" in longitudinal_biomarkers
            or "psa" in longitudinal_biomarkers
            or "ca_125" in longitudinal_biomarkers
            or any(c.icd10_code.startswith("C") or c.icd10_code.startswith("D") for c in normalized_conditions)
        )

        record = NormalizedPatientRecord(
            patient_id=payload.patient_id,
            gender=payload.gender,
            birth_date=payload.birth_date,
            age_years=age_years,
            longitudinal_biomarkers=longitudinal_biomarkers,
            conditions=normalized_conditions,
            medications=normalized_medications,
            clinical_notes=normalized_notes,
            clinical_domain_readiness={
                "diabetes": has_diabetes_data,
                "cardiovascular": has_cvd_data,
                "chronic_kidney_disease": has_ckd_data,
                "cancer": has_cancer_data,
            },
            total_biomarker_measurements=total_measurements,
            earliest_record_date=earliest_date,
            latest_record_date=latest_date,
        )

        return record, [], warnings
