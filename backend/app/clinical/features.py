import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.schemas.emr import NormalizedPatientRecord, NormalizedBiomarkerPoint
from app.schemas.features import (
    HbA1cTrajectoryFeature,
    EGFRTrajectoryFeature,
    SystolicBPTrajectoryFeature,
    LipidBiomarkerFeature,
    SmokingStatusFeature,
    DiabetesHistoryFeature,
    ASCVDClinicalFeatures,
    ClinicalDomainFeatures,
)

DAYS_PER_YEAR = 365.25
SECONDS_PER_DAY = 86400.0


def derive_hba1c_trajectory(
    points: Optional[List[NormalizedBiomarkerPoint]],
) -> HbA1cTrajectoryFeature:
    """
    Derives longitudinal HbA1c trajectory features from chronologically sorted measurements.
    Does not modify original data. Handles single-point or identical timestamps safely.
    """
    if not points:
        return HbA1cTrajectoryFeature(
            available=False,
            status="insufficient_history",
            measurement_count=0,
            unit="%",
        )

    # Work on a copy sorted by timestamp to ensure chronological integrity
    sorted_pts = sorted(points, key=lambda p: p.effective_datetime)
    n = len(sorted_pts)
    latest = sorted_pts[-1]
    unit = latest.unit or "%"

    if n == 1:
        return HbA1cTrajectoryFeature(
            available=True,
            status="single_measurement",
            measurement_count=1,
            latest_value=latest.value,
            latest_timestamp=latest.effective_datetime,
            previous_value=None,
            previous_timestamp=None,
            absolute_change=None,
            time_interval_days=None,
            annualized_rate_of_change=None,
            unit=unit,
        )

    prev = sorted_pts[-2]
    abs_change = round(latest.value - prev.value, 4)
    dt_seconds = (latest.effective_datetime - prev.effective_datetime).total_seconds()
    dt_days = round(dt_seconds / SECONDS_PER_DAY, 2)

    # Identical timestamps check: prevent division by zero
    if dt_seconds == 0:
        return HbA1cTrajectoryFeature(
            available=True,
            status="identical_timestamps",
            measurement_count=n,
            latest_value=latest.value,
            latest_timestamp=latest.effective_datetime,
            previous_value=prev.value,
            previous_timestamp=prev.effective_datetime,
            absolute_change=abs_change,
            time_interval_days=0.0,
            annualized_rate_of_change=None,
            unit=unit,
        )

    years = dt_seconds / (SECONDS_PER_DAY * DAYS_PER_YEAR)
    annualized_rate = round((latest.value - prev.value) / years, 4)

    return HbA1cTrajectoryFeature(
        available=True,
        status="available",
        measurement_count=n,
        latest_value=latest.value,
        latest_timestamp=latest.effective_datetime,
        previous_value=prev.value,
        previous_timestamp=prev.effective_datetime,
        absolute_change=abs_change,
        time_interval_days=dt_days,
        annualized_rate_of_change=annualized_rate,
        unit=unit,
    )


def derive_egfr_trajectory(
    points: Optional[List[NormalizedBiomarkerPoint]],
) -> EGFRTrajectoryFeature:
    """
    Derives eGFR trajectory and annualized slope from longitudinal measurements.
    Uses OLS linear regression slope across all points if n >= 3, or two-point slope if n == 2.
    Safely prevents division by zero if all timestamps are identical.
    """
    if not points:
        return EGFRTrajectoryFeature(
            available=False,
            status="insufficient_history",
            measurement_count=0,
            unit="mL/min/1.73m²",
        )

    sorted_pts = sorted(points, key=lambda p: p.effective_datetime)
    n = len(sorted_pts)
    latest = sorted_pts[-1]
    unit = latest.unit or "mL/min/1.73m²"

    if n == 1:
        return EGFRTrajectoryFeature(
            available=True,
            status="single_measurement",
            measurement_count=1,
            latest_value=latest.value,
            latest_timestamp=latest.effective_datetime,
            previous_value=None,
            previous_timestamp=None,
            absolute_change=None,
            time_interval_days=None,
            annualized_slope=None,
            unit=unit,
        )

    prev = sorted_pts[-2]
    abs_change = round(latest.value - prev.value, 4)
    dt_seconds = (latest.effective_datetime - prev.effective_datetime).total_seconds()
    dt_days = round(dt_seconds / SECONDS_PER_DAY, 2)

    # Prevent division by zero for identical consecutive timestamps
    if dt_seconds == 0:
        return EGFRTrajectoryFeature(
            available=True,
            status="identical_timestamps",
            measurement_count=n,
            latest_value=latest.value,
            latest_timestamp=latest.effective_datetime,
            previous_value=prev.value,
            previous_timestamp=prev.effective_datetime,
            absolute_change=abs_change,
            time_interval_days=0.0,
            annualized_slope=None,
            unit=unit,
        )

    if n == 2:
        # Two-point annualized slope
        years = dt_seconds / (SECONDS_PER_DAY * DAYS_PER_YEAR)
        annualized_slope = round((latest.value - prev.value) / years, 4)
    else:
        # Multi-point Ordinary Least Squares (OLS) linear slope across all points
        t0 = sorted_pts[0].effective_datetime
        x_vals = [(p.effective_datetime - t0).total_seconds() / (SECONDS_PER_DAY * DAYS_PER_YEAR) for p in sorted_pts]
        y_vals = [p.value for p in sorted_pts]

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        s_xx = sum((x - x_mean) ** 2 for x in x_vals)
        s_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))

        if s_xx == 0:
            annualized_slope = None
        else:
            annualized_slope = round(s_xy / s_xx, 4)

    return EGFRTrajectoryFeature(
        available=True,
        status="available",
        measurement_count=n,
        latest_value=latest.value,
        latest_timestamp=latest.effective_datetime,
        previous_value=prev.value,
        previous_timestamp=prev.effective_datetime,
        absolute_change=abs_change,
        time_interval_days=dt_days,
        annualized_slope=annualized_slope,
        unit=unit,
    )


def derive_systolic_bp_trajectory(
    points: Optional[List[NormalizedBiomarkerPoint]],
) -> SystolicBPTrajectoryFeature:
    """
    Derives Systolic Blood Pressure count, latest value, mean, and sample standard deviation (variability).
    Does not invent values when history is insufficient.
    """
    if not points:
        return SystolicBPTrajectoryFeature(
            available=False,
            status="insufficient_history",
            measurement_count=0,
            unit="mmHg",
        )

    sorted_pts = sorted(points, key=lambda p: p.effective_datetime)
    n = len(sorted_pts)
    latest = sorted_pts[-1]
    unit = latest.unit or "mmHg"

    y_vals = [p.value for p in sorted_pts]
    mean_val = round(sum(y_vals) / n, 2)

    if n == 1:
        return SystolicBPTrajectoryFeature(
            available=True,
            status="single_measurement",
            measurement_count=1,
            latest_value=latest.value,
            latest_timestamp=latest.effective_datetime,
            mean=mean_val,
            standard_deviation=None,
            unit=unit,
        )

    # Sample standard deviation (Bessel's correction n-1)
    variance = sum((y - mean_val) ** 2 for y in y_vals) / (n - 1)
    std_dev = round(math.sqrt(variance), 2)

    return SystolicBPTrajectoryFeature(
        available=True,
        status="available",
        measurement_count=n,
        latest_value=latest.value,
        latest_timestamp=latest.effective_datetime,
        mean=mean_val,
        standard_deviation=std_dev,
        unit=unit,
    )


# --- Step 12: ASCVD Biomarker & Clinical Risk Feature Derivation ---

def derive_lipid_feature(
    points: Optional[List[NormalizedBiomarkerPoint]],
    default_unit: str = "mg/dL",
) -> LipidBiomarkerFeature:
    """
    Derives lipid measurement features (total cholesterol or HDL) from longitudinal measurements.
    Preserves units and timestamps without imputation.
    """
    if not points:
        return LipidBiomarkerFeature(
            available=False,
            status="unavailable",
            measurement_count=0,
            unit=default_unit,
        )

    sorted_pts = sorted(points, key=lambda p: p.effective_datetime)
    n = len(sorted_pts)
    latest = sorted_pts[-1]
    unit = latest.unit or default_unit

    if n == 1:
        return LipidBiomarkerFeature(
            available=True,
            status="single_measurement",
            measurement_count=1,
            latest_value=latest.value,
            latest_timestamp=latest.effective_datetime,
            previous_value=None,
            previous_timestamp=None,
            unit=unit,
        )

    prev = sorted_pts[-2]
    return LipidBiomarkerFeature(
        available=True,
        status="available",
        measurement_count=n,
        latest_value=latest.value,
        latest_timestamp=latest.effective_datetime,
        previous_value=prev.value,
        previous_timestamp=prev.effective_datetime,
        unit=unit,
    )


def extract_smoking_status(record: NormalizedPatientRecord) -> SmokingStatusFeature:
    """
    Extracts smoking status from recorded conditions or smoking observations.
    CRITICAL: Does NOT impute missing values. If not documented, explicitly reports unavailable.
    """
    # 1. Check conditions for ICD-10 tobacco codes
    for cond in record.conditions:
        code_upper = cond.icd10_code.upper()
        if code_upper.startswith("F17"):
            return SmokingStatusFeature(
                available=True,
                status="available",
                value="current_smoker" if cond.clinical_status == "active" else "former_smoker",
                source_code=cond.icd10_code,
                source_display=cond.display_name,
                documented_date=str(cond.recorded_date) if cond.recorded_date else None,
            )
        if "Z87.891" in code_upper:
            return SmokingStatusFeature(
                available=True,
                status="available",
                value="former_smoker",
                source_code=cond.icd10_code,
                source_display=cond.display_name,
                documented_date=str(cond.recorded_date) if cond.recorded_date else None,
            )
        if "Z72.0" in code_upper:
            return SmokingStatusFeature(
                available=True,
                status="available",
                value="current_smoker",
                source_code=cond.icd10_code,
                source_display=cond.display_name,
                documented_date=str(cond.recorded_date) if cond.recorded_date else None,
            )

    # 2. Check observations for LOINC 72166-2 (Tobacco smoking status)
    smoking_obs = (
        record.longitudinal_biomarkers.get("smoking_status")
        or record.longitudinal_biomarkers.get("obs_72166_2")
    )
    if smoking_obs:
        latest = smoking_obs[-1]
        status_val = "current_smoker" if latest.value > 0 else "never_smoker"
        return SmokingStatusFeature(
            available=True,
            status="available",
            value=status_val,
            source_code=latest.loinc_code or "72166-2",
            source_display=latest.standard_name,
            documented_date=latest.effective_datetime.isoformat(),
        )

    return SmokingStatusFeature(
        available=False,
        status="unavailable",
        value=None,
        source_code=None,
        source_display=None,
        documented_date=None,
    )


def extract_diabetes_history(record: NormalizedPatientRecord) -> DiabetesHistoryFeature:
    """
    Evaluates diabetes history from conditions, lab criteria (HbA1c >= 6.5%), or medications.
    Explicitly documents clinical evidence. Does NOT guess or impute.
    """
    evidence: List[str] = []

    # 1. Condition check
    for cond in record.conditions:
        code_upper = cond.icd10_code.upper()
        if code_upper.startswith("E10") or code_upper.startswith("E11") or code_upper.startswith("E13"):
            evidence.append(f"Condition: {cond.icd10_code} ({cond.display_name})")

    # 2. Lab check (HbA1c >= 6.5%)
    hba1c_pts = record.longitudinal_biomarkers.get("hba1c")
    if hba1c_pts:
        latest_hba1c = hba1c_pts[-1]
        if latest_hba1c.value >= 6.5:
            evidence.append(f"Laboratory: Latest HbA1c {latest_hba1c.value}% >= 6.5%")

    # 3. Pharmacotherapy check
    antidiabetic_agents = [
        "metformin", "insulin", "glipizide", "glimepiride",
        "semaglutide", "empagliflozin", "dapagliflozin", "sitagliptin"
    ]
    for med in record.medications:
        name_lower = med.display_name.lower()
        if any(agent in name_lower for agent in antidiabetic_agents):
            evidence.append(f"Medication: {med.display_name}")

    if evidence:
        return DiabetesHistoryFeature(
            available=True,
            status="available",
            has_diabetes=True,
            source_evidence=evidence,
        )

    # If clinical record exists with labs or conditions but no diabetes indicators, document as absent
    if record.conditions or record.longitudinal_biomarkers:
        return DiabetesHistoryFeature(
            available=True,
            status="available",
            has_diabetes=False,
            source_evidence=["No documented diabetes ICD-10 diagnosis, medication, or HbA1c >= 6.5% found in record."],
        )

    return DiabetesHistoryFeature(
        available=False,
        status="unavailable",
        has_diabetes=None,
        source_evidence=[],
    )


def derive_ascvd_features(record: NormalizedPatientRecord) -> ASCVDClinicalFeatures:
    """
    Derives ASCVD clinical features strictly from available EMR data.
    Identifies missing required features without imputation.
    """
    now_utc = datetime.now(timezone.utc)
    missing: List[str] = []

    # 1. Age
    age = record.age_years
    age_avail = age is not None and age > 0
    if not age_avail:
        missing.append("age")

    # 2. Gender
    gender = record.gender
    gender_avail = gender is not None and gender.lower() in ("male", "female")
    if not gender_avail:
        missing.append("gender")

    # 3. Systolic BP
    sbp_pts = record.longitudinal_biomarkers.get("systolic_bp")
    sbp_feat = derive_systolic_bp_trajectory(sbp_pts)
    if not sbp_feat.available:
        missing.append("systolic_bp")

    # 4. Total Cholesterol
    tc_pts = record.longitudinal_biomarkers.get("total_cholesterol")
    tc_feat = derive_lipid_feature(tc_pts)
    if not tc_feat.available:
        missing.append("total_cholesterol")

    # 5. HDL Cholesterol
    hdl_pts = record.longitudinal_biomarkers.get("hdl_cholesterol")
    hdl_feat = derive_lipid_feature(hdl_pts)
    if not hdl_feat.available:
        missing.append("hdl_cholesterol")

    # 6. Smoking status
    smoking_feat = extract_smoking_status(record)
    if not smoking_feat.available or smoking_feat.value is None:
        missing.append("smoking_status")

    # 7. Diabetes history
    diabetes_feat = extract_diabetes_history(record)
    if not diabetes_feat.available or diabetes_feat.has_diabetes is None:
        missing.append("diabetes_status")

    return ASCVDClinicalFeatures(
        patient_id=record.patient_id,
        extracted_at=now_utc,
        age_years=age,
        age_available=age_avail,
        gender=gender,
        gender_available=gender_avail,
        systolic_bp=sbp_feat,
        total_cholesterol=tc_feat,
        hdl_cholesterol=hdl_feat,
        smoking_status=smoking_feat,
        diabetes_history=diabetes_feat,
        missing_required_features=missing,
        is_sufficient_for_ascvd=(len(missing) == 0),
    )


def extract_clinical_features(
    record: NormalizedPatientRecord,
    domain: str = "all",
) -> ClinicalDomainFeatures:
    """
    Master feature extraction pipeline connecting a NormalizedPatientRecord to
    trajectory features and ASCVD clinical risk factor features.
    Produces structured trajectory objects, ASCVD feature model, and a deterministic flat feature vector.
    """
    hba1c_pts = record.longitudinal_biomarkers.get("hba1c")
    egfr_pts = record.longitudinal_biomarkers.get("egfr")
    sbp_pts = record.longitudinal_biomarkers.get("systolic_bp")

    hba1c_feat = derive_hba1c_trajectory(hba1c_pts)
    egfr_feat = derive_egfr_trajectory(egfr_pts)
    sbp_feat = derive_systolic_bp_trajectory(sbp_pts)
    ascvd_feat = derive_ascvd_features(record)

    # Flat feature mapping for downstream risk models (Phase 5 / Phase 12)
    feature_vector: Dict[str, Optional[float]] = {
        "hba1c_latest": hba1c_feat.latest_value,
        "hba1c_previous": hba1c_feat.previous_value,
        "hba1c_change": hba1c_feat.absolute_change,
        "hba1c_rate_per_year": hba1c_feat.annualized_rate_of_change,
        "egfr_latest": egfr_feat.latest_value,
        "egfr_previous": egfr_feat.previous_value,
        "egfr_change": egfr_feat.absolute_change,
        "egfr_annualized_slope": egfr_feat.annualized_slope,
        "systolic_bp_latest": sbp_feat.latest_value,
        "systolic_bp_mean": sbp_feat.mean,
        "systolic_bp_variability": sbp_feat.standard_deviation,
        "systolic_bp_count": float(sbp_feat.measurement_count),
        "age": float(record.age_years) if record.age_years is not None else None,
        "total_cholesterol_latest": ascvd_feat.total_cholesterol.latest_value,
        "hdl_cholesterol_latest": ascvd_feat.hdl_cholesterol.latest_value,
        "is_smoker": 1.0 if ascvd_feat.smoking_status.value == "current_smoker" else (0.0 if ascvd_feat.smoking_status.value in ("former_smoker", "never_smoker") else None),
        "has_diabetes": 1.0 if ascvd_feat.diabetes_history.has_diabetes is True else (0.0 if ascvd_feat.diabetes_history.has_diabetes is False else None),
    }

    return ClinicalDomainFeatures(
        patient_id=record.patient_id,
        domain=domain,
        extracted_at=datetime.now(timezone.utc),
        hba1c=hba1c_feat,
        egfr=egfr_feat,
        systolic_bp=sbp_feat,
        ascvd=ascvd_feat,
        feature_vector=feature_vector,
    )

