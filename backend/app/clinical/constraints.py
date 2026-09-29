"""
Clinical Biomarker Validation Ranges and LOINC Ontology Mappings.
These ranges define physiologically plausible boundaries for human electronic medical records.
Values outside these ranges indicate severe laboratory error, typographical entry error, or corrupted data.
"""

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class BiomarkerClinicalConstraint(BaseModel):
    standard_name: str
    loinc_codes: List[str]
    min_plausible: float = Field(..., description="Absolute physiological minimum (inclusive)")
    max_plausible: float = Field(..., description="Absolute physiological maximum (inclusive)")
    standard_unit: str
    clinical_rationale: str


CLINICAL_CONSTRAINTS: Dict[str, BiomarkerClinicalConstraint] = {
    "hba1c": BiomarkerClinicalConstraint(
        standard_name="Hemoglobin A1c",
        loinc_codes=["4548-4", "17856-6"],
        min_plausible=2.0,
        max_plausible=25.0,
        standard_unit="%",
        clinical_rationale="HbA1c below 2% is physiologically incompatible with life; above 25% represents catastrophic assay error or severe interference.",
    ),
    "fasting_glucose": BiomarkerClinicalConstraint(
        standard_name="Fasting Plasma Glucose",
        loinc_codes=["1558-6", "2345-7", "76629-5"],
        min_plausible=15.0,
        max_plausible=1500.0,
        standard_unit="mg/dL",
        clinical_rationale="Blood glucose below 15 mg/dL is lethal hypoglycemia; values exceeding 1500 mg/dL indicate severe hyperosmolar hyperglycemic state or dilution error.",
    ),
    "systolic_bp": BiomarkerClinicalConstraint(
        standard_name="Systolic Blood Pressure",
        loinc_codes=["8480-6"],
        min_plausible=40.0,
        max_plausible=300.0,
        standard_unit="mmHg",
        clinical_rationale="Arterial systolic pressure below 40 mmHg reflects profound cardiovascular collapse; above 300 mmHg is non-physiological.",
    ),
    "diastolic_bp": BiomarkerClinicalConstraint(
        standard_name="Diastolic Blood Pressure",
        loinc_codes=["8462-4"],
        min_plausible=20.0,
        max_plausible=200.0,
        standard_unit="mmHg",
        clinical_rationale="Diastolic pressure below 20 mmHg indicates aortic run-off or arrest; above 200 mmHg reflects extreme hypertensive crisis.",
    ),
    "egfr": BiomarkerClinicalConstraint(
        standard_name="Estimated Glomerular Filtration Rate",
        loinc_codes=["33914-3", "48642-3", "62238-1", "98979-8"],
        min_plausible=0.0,
        max_plausible=200.0,
        standard_unit="mL/min/1.73m²",
        clinical_rationale="eGFR calculated by CKD-EPI formula ranges between 0 (complete renal shutdown/ESRD) and ~200 in hyperfiltration.",
    ),
    "serum_creatinine": BiomarkerClinicalConstraint(
        standard_name="Serum Creatinine",
        loinc_codes=["2160-0", "38483-4"],
        min_plausible=0.1,
        max_plausible=35.0,
        standard_unit="mg/dL",
        clinical_rationale="Creatinine below 0.1 mg/dL is extreme cachexia/lab fault; levels above 35 mg/dL are life-threatening uremia.",
    ),
    "urine_albumin_creatinine_ratio": BiomarkerClinicalConstraint(
        standard_name="Urine Albumin-to-Creatinine Ratio (uACR)",
        loinc_codes=["14959-1", "9318-7"],
        min_plausible=0.0,
        max_plausible=20000.0,
        standard_unit="mg/g",
        clinical_rationale="uACR indicates nephropathy; values above 20,000 mg/g represent massive nephrotic range proteinuria.",
    ),
    "total_cholesterol": BiomarkerClinicalConstraint(
        standard_name="Total Serum Cholesterol",
        loinc_codes=["2093-3"],
        min_plausible=30.0,
        max_plausible=1500.0,
        standard_unit="mg/dL",
        clinical_rationale="Total cholesterol outside 30-1500 mg/dL is biologically implausible outside severe familial hypercholesterolemia assays.",
    ),
    "hdl_cholesterol": BiomarkerClinicalConstraint(
        standard_name="High-Density Lipoprotein (HDL)",
        loinc_codes=["2085-9"],
        min_plausible=5.0,
        max_plausible=200.0,
        standard_unit="mg/dL",
        clinical_rationale="HDL values range between 5 and 200 mg/dL.",
    ),
    "cea": BiomarkerClinicalConstraint(
        standard_name="Carcinoembryonic Antigen (CEA)",
        loinc_codes=["2039-6"],
        min_plausible=0.0,
        max_plausible=10000.0,
        standard_unit="ng/mL",
        clinical_rationale="Oncology epithelial marker; must be non-negative.",
    ),
    "psa": BiomarkerClinicalConstraint(
        standard_name="Prostate-Specific Antigen (PSA)",
        loinc_codes=["2857-1"],
        min_plausible=0.0,
        max_plausible=5000.0,
        standard_unit="ng/mL",
        clinical_rationale="Prostate malignancy screening marker; must be non-negative.",
    ),
    "ca_125": BiomarkerClinicalConstraint(
        standard_name="Cancer Antigen 125 (CA-125)",
        loinc_codes=["10334-1"],
        min_plausible=0.0,
        max_plausible=25000.0,
        standard_unit="U/mL",
        clinical_rationale="Adnexal and ovarian oncology marker; must be non-negative.",
    ),
}

# Reverse lookup dictionary: loinc_code -> constraint_key
LOINC_TO_BIOMARKER_KEY: Dict[str, str] = {}
for key, constraint in CLINICAL_CONSTRAINTS.items():
    for loinc in constraint.loinc_codes:
        LOINC_TO_BIOMARKER_KEY[loinc] = key
        # Also map without hyphens for flexible EHR input
        LOINC_TO_BIOMARKER_KEY[loinc.replace("-", "")] = key
