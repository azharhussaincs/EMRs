from typing import Dict, List
from fastapi import APIRouter, HTTPException, status
from app.clinical.domains import CLINICAL_DOMAINS_REGISTRY, DiseaseDomainRegistryEntry
from app.core.config import ClinicalDomain

router = APIRouter()


@router.get("", response_model=List[DiseaseDomainRegistryEntry], summary="List Registered Clinical Domains")
async def list_clinical_domains() -> List[DiseaseDomainRegistryEntry]:
    """
    Returns full clinical metadata, LOINC biomarkers, and consensus clinical guidelines
    for the 4 core chronic disease areas: Diabetes, CVD, CKD, and Cancer.
    """
    return list(CLINICAL_DOMAINS_REGISTRY.values())


@router.get("/{domain}", response_model=DiseaseDomainRegistryEntry, summary="Get Specific Clinical Domain Spec")
async def get_clinical_domain(domain: ClinicalDomain) -> DiseaseDomainRegistryEntry:
    """Returns domain specification for a specific disease risk area."""
    if domain not in CLINICAL_DOMAINS_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical domain '{domain}' is not registered.",
        )
    return CLINICAL_DOMAINS_REGISTRY[domain]
