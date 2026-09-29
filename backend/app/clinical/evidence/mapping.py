from typing import List, Set
from app.schemas.evidence import EvidenceDomainCategory


def map_clinical_features_to_evidence_domains(
    feature_names: List[str],
    has_comorbid_ckd: bool = False,
) -> List[EvidenceDomainCategory]:
    """
    Explicit, deterministic mapping between verified clinical feature keys and relevant evidence domains.

    CRITICAL SAFETY RULES:
    1. Identifies relevant clinical evidence domains ONLY.
    2. Does NOT generate or infer clinical treatment advice or medication directives.
    3. Pure, deterministic mapping without probabilistic assumptions.
    """
    categories: Set[EvidenceDomainCategory] = set()

    for feat in feature_names:
        feat_clean = feat.lower()
        if "hba1c_latest" in feat_clean or "hba1c_previous" in feat_clean:
            categories.add(EvidenceDomainCategory.HBA1C_MONITORING)
            categories.add(EvidenceDomainCategory.DIABETES_CLASSIFICATION_CONTEXT)

        if "hba1c_change" in feat_clean or "hba1c_annualized_rate" in feat_clean:
            categories.add(EvidenceDomainCategory.GLYCEMIC_TRAJECTORY_ASSESSMENT)

        if "egfr" in feat_clean or "creatinine" in feat_clean:
            categories.add(EvidenceDomainCategory.DIABETES_CKD_INTERSECTION)

        if "systolic_bp" in feat_clean or "cholesterol" in feat_clean or "ascvd" in feat_clean or "smoking" in feat_clean:
            categories.add(EvidenceDomainCategory.CARDIOVASCULAR_RISK_EXPANSION)

    if has_comorbid_ckd:
        categories.add(EvidenceDomainCategory.DIABETES_CKD_INTERSECTION)

    # Return ordered list for determinism
    return sorted(list(categories), key=lambda c: c.value)
