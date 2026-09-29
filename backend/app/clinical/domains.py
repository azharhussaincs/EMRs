from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.config import ClinicalDomain


class ClinicalBiomarkerSpec(BaseModel):
    name: str = Field(..., description="Biomarker standard name")
    loinc_code: Optional[str] = Field(None, description="LOINC ontology code")
    unit: str = Field(..., description="Standard clinical measurement unit")
    description: str = Field(..., description="Clinical diagnostic significance")


class ClinicalGuidelineReference(BaseModel):
    organization: str = Field(..., description="Publishing body, e.g. ADA, ACC/AHA, KDIGO, NCCN")
    title: str = Field(..., description="Guideline title")
    edition_year: int = Field(..., description="Publication year")
    evidence_level: str = Field(..., description="Clinical evidence grade (e.g., Level A, Level B)")
    url: Optional[str] = Field(None, description="Official reference URI")


class DiseaseDomainRegistryEntry(BaseModel):
    domain: ClinicalDomain
    display_name: str
    icd10_family: List[str]
    snomed_ct_concept: Optional[str]
    description: str
    primary_biomarkers: List[ClinicalBiomarkerSpec]
    consensus_guidelines: List[ClinicalGuidelineReference]
    target_risk_horizons: List[str]  # e.g. ["1-year", "5-year", "10-year"]


# Canonical Clinical Domain Registry
CLINICAL_DOMAINS_REGISTRY: Dict[ClinicalDomain, DiseaseDomainRegistryEntry] = {
    ClinicalDomain.DIABETES: DiseaseDomainRegistryEntry(
        domain=ClinicalDomain.DIABETES,
        display_name="Type 2 Diabetes Mellitus & Complications",
        icd10_family=["E11", "E11.9", "E11.65", "E11.22"],
        snomed_ct_concept="44054006",
        description="Assessment of glycemic trajectory, conversion from prediabetes, and microvascular/macrovascular complication risk.",
        primary_biomarkers=[
            ClinicalBiomarkerSpec(name="Hemoglobin A1c", loinc_code="4548-4", unit="%", description="Glycated hemoglobin index over past 90 days"),
            ClinicalBiomarkerSpec(name="Fasting Plasma Glucose", loinc_code="1558-6", unit="mg/dL", description="Baseline fasting glycemic measurement"),
            ClinicalBiomarkerSpec(name="Body Mass Index", loinc_code="39156-5", unit="kg/m²", description="Anthropometric obesity metric"),
        ],
        consensus_guidelines=[
            ClinicalGuidelineReference(
                organization="American Diabetes Association (ADA)",
                title="Standards of Care in Diabetes",
                edition_year=2024,
                evidence_level="Level A",
                url="https://diabetesjournals.org/care/issue/47/Supplement_1",
            )
        ],
        target_risk_horizons=["3-year", "5-year", "10-year"],
    ),
    ClinicalDomain.CARDIOVASCULAR: DiseaseDomainRegistryEntry(
        domain=ClinicalDomain.CARDIOVASCULAR,
        display_name="Atherosclerotic Cardiovascular Disease (ASCVD) & Heart Failure",
        icd10_family=["I25.10", "I21.9", "I50.9", "I10"],
        snomed_ct_concept="49436004",
        description="Assessment of 10-year primary ASCVD event risk (myocardial infarction, stroke) and decompensated heart failure.",
        primary_biomarkers=[
            ClinicalBiomarkerSpec(name="Systolic Blood Pressure", loinc_code="8480-6", unit="mmHg", description="Resting systolic arterial pressure"),
            ClinicalBiomarkerSpec(name="Total Cholesterol", loinc_code="2093-3", unit="mg/dL", description="Total serum cholesterol"),
            ClinicalBiomarkerSpec(name="HDL Cholesterol", loinc_code="2085-9", unit="mg/dL", description="High-density lipoprotein cholesterol"),
            ClinicalBiomarkerSpec(name="High-Sensitivity Troponin", loinc_code="89579-7", unit="ng/L", description="Myocardial injury marker"),
        ],
        consensus_guidelines=[
            ClinicalGuidelineReference(
                organization="American College of Cardiology / American Heart Association (ACC/AHA)",
                title="Guideline on the Primary Prevention of Cardiovascular Disease",
                edition_year=2019,
                evidence_level="Class I / Level A",
                url="https://www.ahajournals.org/doi/10.1161/CIR.0000000000000678",
            )
        ],
        target_risk_horizons=["5-year", "10-year", "Lifetime"],
    ),
    ClinicalDomain.CHRONIC_KIDNEY_DISEASE: DiseaseDomainRegistryEntry(
        domain=ClinicalDomain.CHRONIC_KIDNEY_DISEASE,
        display_name="Chronic Kidney Disease (CKD) Progression",
        icd10_family=["N18.1", "N18.2", "N18.3", "N18.4", "N18.5", "N18.6"],
        snomed_ct_concept="709044004",
        description="Progression across KDIGO G1-G5 staging, annual eGFR trajectory, and risk of End-Stage Renal Disease (ESRD).",
        primary_biomarkers=[
            ClinicalBiomarkerSpec(name="Estimated Glomerular Filtration Rate (eGFR)", loinc_code="33914-3", unit="mL/min/1.73m²", description="CKD-EPI formula filtered creatinine indicator"),
            ClinicalBiomarkerSpec(name="Urine Albumin-to-Creatinine Ratio (uACR)", loinc_code="14959-1", unit="mg/g", description="Renal microalbuminuria damage marker"),
            ClinicalBiomarkerSpec(name="Serum Creatinine", loinc_code="2160-0", unit="mg/dL", description="Serum byproduct of muscle metabolism"),
        ],
        consensus_guidelines=[
            ClinicalGuidelineReference(
                organization="Kidney Disease: Improving Global Outcomes (KDIGO)",
                title="Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
                edition_year=2024,
                evidence_level="Grade 1A",
                url="https://kdigo.org/guidelines/ckd-evaluation-and-management/",
            )
        ],
        target_risk_horizons=["1-year", "2-year", "5-year"],
    ),
    ClinicalDomain.CANCER: DiseaseDomainRegistryEntry(
        domain=ClinicalDomain.CANCER,
        display_name="Oncology Early Detection & Malignancy Screening",
        icd10_family=["C00-D49", "C34.90", "C50.919", "C18.9"],
        snomed_ct_concept="363346000",
        description="Evaluation of clinical suspicion, hereditary predisposition, and screening protocol adherence across solid tumors.",
        primary_biomarkers=[
            ClinicalBiomarkerSpec(name="Carcinoembryonic Antigen (CEA)", loinc_code="2039-6", unit="ng/mL", description="Colorectal & epithelial tumor marker"),
            ClinicalBiomarkerSpec(name="Prostate-Specific Antigen (PSA)", loinc_code="2857-1", unit="ng/mL", description="Prostate malignancy screening marker"),
            ClinicalBiomarkerSpec(name="CA-125", loinc_code="10334-1", unit="U/mL", description="Ovarian and adnexal tumor marker"),
        ],
        consensus_guidelines=[
            ClinicalGuidelineReference(
                organization="National Comprehensive Cancer Network (NCCN)",
                title="NCCN Clinical Practice Guidelines in Oncology: Detection, Prevention, & Risk Assessment",
                edition_year=2024,
                evidence_level="Category 1",
                url="https://www.nccn.org/guidelines/category_1",
            )
        ],
        target_risk_horizons=["1-year", "5-year"],
    ),
}
