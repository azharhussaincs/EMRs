import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import ClinicalDomain
from app.core.audit import audit_service
from app.schemas.evidence import (
    EvidenceSourceRegistryEntry,
    ClinicalEvidenceReference,
    EvidenceStatus,
    EvidenceDomainCategory,
    EvidenceRetrievalResponse,
)
from app.clinical.evidence.registry import (
    EVIDENCE_SOURCE_REGISTRY,
    VERIFIED_EVIDENCE_REFERENCES,
)
from app.clinical.evidence.provider import curated_evidence_provider
from app.clinical.evidence.mapping import map_clinical_features_to_evidence_domains


def test_1_evidence_source_registry_validation():
    # Verify authoritative registries are present with real publication metadata
    assert "ADA-SOC-2026" in EVIDENCE_SOURCE_REGISTRY
    assert "KDIGO-CKD-DM-2022" in EVIDENCE_SOURCE_REGISTRY
    assert "ACC-AHA-PPCVD-2019" in EVIDENCE_SOURCE_REGISTRY

    ada = EVIDENCE_SOURCE_REGISTRY["ADA-SOC-2026"]
    assert ada.edition_year == 2026
    assert "American Diabetes Association" in ada.organization
    assert "Diabetes Care" in ada.citation_metadata
    assert ada.official_url.startswith("https://")
    assert ada.publication_status == "published_current"

    kdigo = EVIDENCE_SOURCE_REGISTRY["KDIGO-CKD-DM-2022"]
    assert kdigo.edition_year == 2022
    assert "Kidney Disease: Improving Global Outcomes" in kdigo.organization
    assert kdigo.publication_status == "published_current"


def test_2_clinical_evidence_reference_schema():
    ref = VERIFIED_EVIDENCE_REFERENCES[0]
    assert isinstance(ref, ClinicalEvidenceReference)
    assert ref.evidence_id.startswith("ev-")
    assert ref.evidence_status == EvidenceStatus.VERIFIED
    assert ref.official_url.startswith("https://")
    assert ref.citation_text != ""


def test_3_verified_citation_metadata_not_fabricated():
    # Strict safety rule: Recommendation IDs must NOT be fabricated
    for ref in VERIFIED_EVIDENCE_REFERENCES:
        assert ref.recommendation_identifier is None, "Must not fabricate recommendation numbers"
        # Confirm authentic publication metadata
        assert ref.publication_version != ""
        assert ref.citation_text != ""
        assert ref.scope_description != ""
        # Must not contain treatment directives in scope
        assert "prescribe" not in ref.scope_description.lower()
        assert "dose" not in ref.scope_description.lower()


def test_4_unavailable_evidence_handling():
    # Querying for category not matching diabetes
    refs = curated_evidence_provider.get_references_by_domain(
        domain=ClinicalDomain.DIABETES,
        category=EvidenceDomainCategory.CARDIOVASCULAR_RISK_EXPANSION,
    )
    assert len(refs) == 0, "Must return empty list without fabricating references"

    # Querying by nonexistent evidence ID
    ref = curated_evidence_provider.get_reference_by_id("nonexistent-evidence-id")
    assert ref is None


def test_5_deterministic_evidence_retrieval():
    refs_run1 = curated_evidence_provider.get_references_by_domain(ClinicalDomain.DIABETES)
    refs_run2 = curated_evidence_provider.get_references_by_domain(ClinicalDomain.DIABETES)

    assert len(refs_run1) == len(refs_run2)
    for r1, r2 in zip(refs_run1, refs_run2):
        assert r1.evidence_id == r2.evidence_id
        assert r1.citation_text == r2.citation_text


def test_6_feature_to_evidence_domain_mapping():
    # HbA1c latest maps to monitoring and classification
    domains1 = map_clinical_features_to_evidence_domains(["hba1c_latest"])
    assert EvidenceDomainCategory.HBA1C_MONITORING in domains1
    assert EvidenceDomainCategory.DIABETES_CLASSIFICATION_CONTEXT in domains1

    # Annualized rate maps to trajectory assessment
    domains2 = map_clinical_features_to_evidence_domains(["hba1c_annualized_rate"])
    assert EvidenceDomainCategory.GLYCEMIC_TRAJECTORY_ASSESSMENT in domains2

    # Comorbid CKD maps to intersection
    domains3 = map_clinical_features_to_evidence_domains(["egfr"], has_comorbid_ckd=True)
    assert EvidenceDomainCategory.DIABETES_CKD_INTERSECTION in domains3

    # Pure function determinism
    assert map_clinical_features_to_evidence_domains(["hba1c_latest"]) == domains1


def test_7_evidence_provider_contract():
    assert curated_evidence_provider.provider_id == "curated_evidence_provider_v1"
    assert curated_evidence_provider.provider_version == "1.0.0-foundation"

    sources = curated_evidence_provider.list_sources()
    assert len(sources) >= 3

    ref = curated_evidence_provider.get_reference_by_id("ev-ada-2026-sec6-glycemic-monitoring")
    assert ref is not None
    assert ref.source_id == "ADA-SOC-2026"


@pytest.mark.asyncio
async def test_8_api_get_diabetes_evidence_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/evidence/diabetes")
        assert res.status_code == 200
        data = res.json()

        assert data["domain"] == "diabetes"
        assert data["total_references"] >= 3
        assert data["provider_id"] == "curated_evidence_provider_v1"
        assert len(data["references"]) >= 3

        # Check reference structure
        first_ref = data["references"][0]
        assert "evidence_id" in first_ref
        assert "source_id" in first_ref
        assert "citation_text" in first_ref
        assert "official_url" in first_ref
        assert first_ref["recommendation_identifier"] is None


@pytest.mark.asyncio
async def test_9_api_get_evidence_sources_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/evidence/sources")
        assert res.status_code == 200
        sources = res.json()
        assert len(sources) >= 3
        source_ids = [s["source_id"] for s in sources]
        assert "ADA-SOC-2026" in source_ids


@pytest.mark.asyncio
async def test_10_audit_traceability_and_phi_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/api/v1/evidence/diabetes?patient_id=PT-EVID-TEST-99",
            headers={"X-Actor-ID": "dr-researcher-07"},
        )
        assert res.status_code == 200

        # Check HIPAA audit trail
        events = audit_service.get_recent_events()
        matching = [
            e for e in events
            if e.action == "retrieve_diabetes_evidence"
            and e.resource_id == "PT-EVID-TEST-99"
            and e.actor_id == "dr-researcher-07"
        ]
        assert len(matching) >= 1
        audit_event = matching[-1]
        assert audit_event.status == "success"
        assert "evidence_request_id" in audit_event.metadata
        assert "evidence_ids_returned" in audit_event.metadata
        assert len(audit_event.metadata["evidence_ids_returned"]) >= 1

        # PHI isolation: verify no patient notes or clinical free-text is logged
        audit_dump = audit_event.model_dump_json()
        assert "clinical_notes" not in audit_dump
        assert "resourceType" not in audit_dump
