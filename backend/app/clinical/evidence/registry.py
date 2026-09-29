from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.core.config import ClinicalDomain
from app.schemas.evidence import (
    EvidenceSourceRegistryEntry,
    ClinicalEvidenceReference,
    EvidenceStatus,
    EvidenceDomainCategory,
)

# Canonical Authoritative Evidence Source Registry
EVIDENCE_SOURCE_REGISTRY: Dict[str, EvidenceSourceRegistryEntry] = {
    "ADA-SOC-2026": EvidenceSourceRegistryEntry(
        source_id="ADA-SOC-2026",
        organization="American Diabetes Association (ADA)",
        title="Standards of Care in Diabetes—2026",
        edition_year=2026,
        guideline_identifier="ADA-SOC-2026",
        official_url="https://diabetesjournals.org/care/issue/49/Supplement_1",
        domain=ClinicalDomain.DIABETES,
        publication_status="published_current",
        retrieval_date="2026-01-01",
        citation_metadata="American Diabetes Association. Standards of Care in Diabetes—2026. Diabetes Care 2026;49(Suppl. 1):S1–S320.",
    ),
    "KDIGO-CKD-DM-2022": EvidenceSourceRegistryEntry(
        source_id="KDIGO-CKD-DM-2022",
        organization="Kidney Disease: Improving Global Outcomes (KDIGO)",
        title="KDIGO 2022 Clinical Practice Guideline for Diabetes Management in Chronic Kidney Disease",
        edition_year=2022,
        guideline_identifier="KDIGO-CKD-DM-2022",
        official_url="https://kdigo.org/guidelines/diabetes-ckd/",
        domain=ClinicalDomain.CHRONIC_KIDNEY_DISEASE,
        publication_status="published_current",  # 2026 edition under development
        retrieval_date="2022-11-01",
        citation_metadata="Kidney Disease: Improving Global Outcomes (KDIGO) Diabetes Work Group. Kidney Int. 2022;102(5S):S1-S127.",
    ),
    "ACC-AHA-PPCVD-2019": EvidenceSourceRegistryEntry(
        source_id="ACC-AHA-PPCVD-2019",
        organization="American College of Cardiology / American Heart Association (ACC/AHA)",
        title="2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease",
        edition_year=2019,
        guideline_identifier="ACC-AHA-PPCVD-2019",
        official_url="https://www.ahajournals.org/doi/10.1161/CIR.0000000000000678",
        domain=ClinicalDomain.CARDIOVASCULAR,
        publication_status="published_current",
        retrieval_date="2019-09-01",
        citation_metadata="Arnett DK, et al. 2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease. Circulation. 2019;140:e596–e646.",
    ),
}


# Curated Verified Clinical Evidence References
VERIFIED_EVIDENCE_REFERENCES: List[ClinicalEvidenceReference] = [
    ClinicalEvidenceReference(
        evidence_id="ev-ada-2026-sec6-glycemic-monitoring",
        source_id="ADA-SOC-2026",
        organization="American Diabetes Association (ADA)",
        guideline_title="Standards of Care in Diabetes—2026",
        publication_version="2026 Edition",
        section_chapter="Section 6: Glycemic Goals and Hypoglycemia",
        recommendation_identifier=None,  # Not fabricated; explicitly None
        citation_text="American Diabetes Association. 6. Glycemic Goals and Hypoglycemia: Standards of Care in Diabetes—2026. Diabetes Care 2026;49(Suppl. 1):S91–S104.",
        official_url="https://diabetesjournals.org/care/issue/49/Supplement_1",
        evidence_status=EvidenceStatus.VERIFIED,
        domain_category=EvidenceDomainCategory.HBA1C_MONITORING,
        scope_description="Guidance regarding frequency and clinical interpretation of glycated hemoglobin (HbA1c) testing.",
        retrieved_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    ),
    ClinicalEvidenceReference(
        evidence_id="ev-ada-2026-sec2-classification",
        source_id="ADA-SOC-2026",
        organization="American Diabetes Association (ADA)",
        guideline_title="Standards of Care in Diabetes—2026",
        publication_version="2026 Edition",
        section_chapter="Section 2: Diagnosis and Classification of Diabetes",
        recommendation_identifier=None,
        citation_text="American Diabetes Association. 2. Diagnosis and Classification of Diabetes: Standards of Care in Diabetes—2026. Diabetes Care 2026;49(Suppl. 1):S20–S42.",
        official_url="https://diabetesjournals.org/care/issue/49/Supplement_1",
        evidence_status=EvidenceStatus.VERIFIED,
        domain_category=EvidenceDomainCategory.DIABETES_CLASSIFICATION_CONTEXT,
        scope_description="Standardized diagnostic thresholds and laboratory confirmation criteria for glycemic assessment.",
        retrieved_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    ),
    ClinicalEvidenceReference(
        evidence_id="ev-ada-2026-glycemic-trajectory",
        source_id="ADA-SOC-2026",
        organization="American Diabetes Association (ADA)",
        guideline_title="Standards of Care in Diabetes—2026",
        publication_version="2026 Edition",
        section_chapter="Section 6: Glycemic Goals and Hypoglycemia",
        recommendation_identifier=None,
        citation_text="American Diabetes Association. 6. Glycemic Goals and Hypoglycemia: Standards of Care in Diabetes—2026. Diabetes Care 2026;49(Suppl. 1):S91–S104.",
        official_url="https://diabetesjournals.org/care/issue/49/Supplement_1",
        evidence_status=EvidenceStatus.VERIFIED,
        domain_category=EvidenceDomainCategory.GLYCEMIC_TRAJECTORY_ASSESSMENT,
        scope_description="Longitudinal evaluation of glycemic trends and rate of change between serial HbA1c observations.",
        retrieved_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    ),
    ClinicalEvidenceReference(
        evidence_id="ev-kdigo-2022-diabetes-ckd",
        source_id="KDIGO-CKD-DM-2022",
        organization="Kidney Disease: Improving Global Outcomes (KDIGO)",
        guideline_title="KDIGO 2022 Clinical Practice Guideline for Diabetes Management in Chronic Kidney Disease",
        publication_version="2022 Guideline (2026 update in development)",
        section_chapter="Chapter 1: Comprehensive Care in Patients with Diabetes and CKD",
        recommendation_identifier=None,
        citation_text="KDIGO Diabetes Work Group. KDIGO 2022 Clinical Practice Guideline for Diabetes Management in Chronic Kidney Disease. Kidney Int. 2022;102(5S):S1–S127.",
        official_url="https://kdigo.org/guidelines/diabetes-ckd/",
        evidence_status=EvidenceStatus.VERIFIED,
        domain_category=EvidenceDomainCategory.DIABETES_CKD_INTERSECTION,
        scope_description="Guidance on glycemic monitoring accuracy and renal risk considerations in comorbid diabetes and chronic kidney disease.",
        retrieved_at=datetime(2022, 11, 1, 0, 0, tzinfo=timezone.utc),
    ),
    ClinicalEvidenceReference(
        evidence_id="ev-acc-2019-primary-prevention-cvd",
        source_id="ACC-AHA-PPCVD-2019",
        organization="American College of Cardiology / American Heart Association (ACC/AHA)",
        guideline_title="2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease",
        publication_version="2019 Guideline",
        section_chapter="Section 3.1: Assessment of Cardiovascular Risk",
        recommendation_identifier=None,
        citation_text="Arnett DK, et al. 2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease. Circulation. 2019;140:e596–e646.",
        official_url="https://www.ahajournals.org/doi/10.1161/CIR.0000000000000678",
        evidence_status=EvidenceStatus.VERIFIED,
        domain_category=EvidenceDomainCategory.CARDIOVASCULAR_RISK_EXPANSION,
        scope_description="Clinical assessment of 10-year risk for atherosclerotic cardiovascular disease using traditional risk factors.",
        retrieved_at=datetime(2019, 9, 1, 0, 0, tzinfo=timezone.utc),
    ),
]

