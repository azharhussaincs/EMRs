import pytest
from datetime import datetime, timezone, timedelta
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_sample_fhir_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/emr/sample-fhir")
    assert response.status_code == 200
    data = response.json()
    assert data["resourceType"] == "Bundle"
    assert len(data["entry"]) > 5


@pytest.mark.asyncio
async def test_fhir_bundle_ingestion_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Fetch authentic sample FHIR bundle
        sample_res = await ac.get("/api/v1/emr/sample-fhir")
        bundle = sample_res.json()

        # 2. Validate first
        val_res = await ac.post("/api/v1/emr/validate", json=bundle)
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data["valid"] is True
        assert val_data["patient_id"] == "PT-CARDIO-RENAL-508"

        # 3. Ingest
        ingest_res = await ac.post("/api/v1/emr/ingest", json=bundle)
        assert ingest_res.status_code == 201
        ingest_data = ingest_res.json()
        assert ingest_data["status"] == "ingested"
        assert ingest_data["audit_event_id"] is not None

        record = ingest_data["patient_record"]
        assert record["patient_id"] == "PT-CARDIO-RENAL-508"
        assert record["gender"] == "male"
        assert record["age_years"] is not None

        # Verify longitudinal sequence for HbA1c (3 measurements)
        hba1c_pts = record["longitudinal_biomarkers"]["hba1c"]
        assert len(hba1c_pts) == 3
        # Check chronological ascending sort
        dates = [pt["effective_datetime"] for pt in hba1c_pts]
        assert dates == sorted(dates)
        assert hba1c_pts[0]["value"] == 7.1
        assert hba1c_pts[2]["value"] == 8.2

        # Verify multi-component blood pressure was normalized
        assert "systolic_bp" in record["longitudinal_biomarkers"]
        assert "diastolic_bp" in record["longitudinal_biomarkers"]
        assert record["longitudinal_biomarkers"]["systolic_bp"][0]["value"] == 142.0
        assert record["longitudinal_biomarkers"]["diastolic_bp"][0]["value"] == 88.0

        # Verify domain readiness
        assert record["clinical_domain_readiness"]["diabetes"] is True
        assert record["clinical_domain_readiness"]["cardiovascular"] is True
        assert record["clinical_domain_readiness"]["chronic_kidney_disease"] is True

        # 4. Verify patient retrieval endpoint
        pat_res = await ac.get("/api/v1/emr/patients/PT-CARDIO-RENAL-508")
        assert pat_res.status_code == 200
        assert pat_res.json()["patient_id"] == "PT-CARDIO-RENAL-508"


@pytest.mark.asyncio
async def test_rejection_physiologically_impossible_hba1c():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        invalid_payload = {
            "patient_id": "PT-INVALID-HBA1C",
            "birth_date": "1980-01-01",
            "observations": [
                {
                    "observation_id": "obs-hba1c-err",
                    "code": {"system": "http://loinc.org", "code": "4548-4", "display": "HbA1c"},
                    "effective_datetime": "2026-01-10T09:00:00Z",
                    "value_numeric": 35.0,  # Impossible: exceeds 25.0%
                    "unit": "%",
                }
            ],
            "conditions": [],
            "medications": [],
            "clinical_notes": [],
        }

        # 1. Validation endpoint returns valid=False with error details
        val_res = await ac.post("/api/v1/emr/validate", json=invalid_payload)
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data["valid"] is False
        assert len(val_data["errors"]) > 0
        assert val_data["errors"][0]["code"] == "PHYSIOLOGICAL_RANGE_EXCEEDED"

        # 2. Ingest endpoint rejects with HTTP 422
        ingest_res = await ac.post("/api/v1/emr/ingest", json=invalid_payload)
        assert ingest_res.status_code == 422
        err_data = ingest_res.json()
        assert err_data["error_type"] == "EMRValidationError"
        assert "35.0" in err_data["errors"][0]["issue"]


@pytest.mark.asyncio
async def test_rejection_blood_pressure_inversion():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        invalid_bp_payload = {
            "patient_id": "PT-INVALID-BP",
            "birth_date": "1975-05-20",
            "observations": [
                {
                    "observation_id": "obs-sys",
                    "code": {"system": "http://loinc.org", "code": "8480-6", "display": "Systolic BP"},
                    "effective_datetime": "2026-01-10T10:00:00Z",
                    "value_numeric": 70.0,
                    "unit": "mmHg",
                },
                {
                    "observation_id": "obs-dia",
                    "code": {"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic BP"},
                    "effective_datetime": "2026-01-10T10:00:00Z",
                    "value_numeric": 110.0,  # Diastolic > Systolic!
                    "unit": "mmHg",
                },
            ],
            "conditions": [],
            "medications": [],
            "clinical_notes": [],
        }

        ingest_res = await ac.post("/api/v1/emr/ingest", json=invalid_bp_payload)
        assert ingest_res.status_code == 422
        err_data = ingest_res.json()
        assert err_data["errors"][0]["code"] == "BLOOD_PRESSURE_INVERSION"


@pytest.mark.asyncio
async def test_rejection_future_timestamp():
    future_time = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        future_payload = {
            "patient_id": "PT-FUTURE",
            "birth_date": "1990-01-01",
            "observations": [
                {
                    "observation_id": "obs-future",
                    "code": {"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine"},
                    "effective_datetime": future_time,
                    "value_numeric": 1.1,
                    "unit": "mg/dL",
                }
            ],
            "conditions": [],
            "medications": [],
            "clinical_notes": [],
        }

        ingest_res = await ac.post("/api/v1/emr/ingest", json=future_payload)
        assert ingest_res.status_code == 422
        err_data = ingest_res.json()
        assert err_data["errors"][0]["code"] == "FUTURE_TIMESTAMP_REJECTED"


@pytest.mark.asyncio
async def test_rejection_negative_creatinine():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        neg_payload = {
            "patient_id": "PT-NEG-LAB",
            "birth_date": "1985-02-14",
            "observations": [
                {
                    "observation_id": "obs-creat-neg",
                    "code": {"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine"},
                    "effective_datetime": "2026-01-10T10:00:00Z",
                    "value_numeric": -1.5,  # Impossible negative
                    "unit": "mg/dL",
                }
            ],
            "conditions": [],
            "medications": [],
            "clinical_notes": [],
        }

        ingest_res = await ac.post("/api/v1/emr/ingest", json=neg_payload)
        assert ingest_res.status_code == 422
        err_data = ingest_res.json()
        assert err_data["errors"][0]["code"] == "PHYSIOLOGICAL_RANGE_EXCEEDED"
