import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings, ClinicalDomain


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == settings.PROJECT_NAME
    assert data["version"] == settings.PROJECT_VERSION
    assert data["api_v1_prefix"] == "/api/v1"


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "emr_ingestion" in data["subsystems"]
    assert "risk_engines" in data["subsystems"]
    assert "genai_provider" in data["subsystems"]
    assert "audit_system" in data["subsystems"]
    assert len(data["active_clinical_domains"]) == 4


@pytest.mark.asyncio
async def test_clinical_domains_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/clinical/domains")
    assert response.status_code == 200
    domains = response.json()
    assert len(domains) == 4
    domain_names = [d["domain"] for d in domains]
    assert "diabetes" in domain_names
    assert "cardiovascular" in domain_names
    assert "chronic_kidney_disease" in domain_names
    assert "cancer" in domain_names


@pytest.mark.asyncio
async def test_emr_validate_and_audit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        emr_payload = {
            "patient_id": "PT-TEST-001",
            "birth_date": "1965-04-12",
            "gender": "female",
            "observations": [
                {
                    "observation_id": "obs-1",
                    "code": {"system": "http://loinc.org", "code": "4548-4", "display": "HbA1c"},
                    "effective_datetime": "2026-01-15T09:30:00Z",
                    "value_numeric": 7.4,
                    "unit": "%",
                }
            ],
            "conditions": [
                {
                    "condition_id": "cond-1",
                    "code": {"system": "http://hl7.org/fhir/sid/icd-10", "code": "E11.9", "display": "Type 2 diabetes"},
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                }
            ],
            "medications": [],
            "clinical_notes": [],
        }

        # Test validation
        val_res = await ac.post("/api/v1/emr/validate", json=emr_payload)
        assert val_res.status_code == 200
        assert val_res.json()["valid"] is True

        # Test ingestion
        ingest_res = await ac.post("/api/v1/emr/ingest", json=emr_payload)
        assert ingest_res.status_code == 201
        ingest_data = ingest_res.json()
        assert ingest_data["patient_record"]["patient_id"] == "PT-TEST-001"
        assert ingest_data["patient_record"]["total_biomarker_measurements"] == 1
        assert len(ingest_data["patient_record"]["conditions"]) == 1

        # Test audit log verification
        audit_res = await ac.get("/api/v1/audit/logs")
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert len(logs) > 0
        last_log = logs[-1]
        assert last_log["resource_id"] == "PT-TEST-001"
        assert last_log["action"] == "ingest_patient_emr"
        assert last_log["integrity_hash"] is not None
