# Generative AI-Based Clinical Risk Assessment Platform (EMR)

A production-grade, research-caliber clinical decision support platform designed to ingest longitudinal Electronic Medical Records (EMRs) and evaluate calibrated risk trajectories across four core chronic disease areas:

1. **Type 2 Diabetes Mellitus & Complications** (ADA Standards of Care)
2. **Atherosclerotic Cardiovascular Disease (ASCVD) & Heart Failure** (ACC/AHA Prevention Guidelines)
3. **Chronic Kidney Disease (CKD) Progression** (KDIGO Clinical Practice Guidelines)
4. **Oncology Early Detection & Malignancy Screening** (NCCN Guidelines)

---

## Architecture Principles
* **Production Healthcare Quality**: Zero fake clinical claims, zero dummy predictions, real clinical ontologies (LOINC, SNOMED-CT, ICD-10-CM, RxNorm).
* **Strict Privacy & Compliance**: Adherence to HIPAA §164.312(b) with an immutable, cryptographically hashed audit trail.
* **Evidence-Grounded GenAI**: All generative explanations are anchored to consensus medical guidelines with verifiable citations.
* **Modular Extensibility**: Abstract base interfaces for EMR ingestion adapters, predictive ML engines, GenAI orchestrators, and vector RAG knowledge bases.

---

## Directory Structure

```
EMRs/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── health.py             # System & subsystem readiness probes
│   │   │   │   │   ├── clinical_domains.py   # 4 core disease metadata & biomarkers
│   │   │   │   │   ├── emr.py                # FHIR R4 ingestion & validation
│   │   │   │   │   ├── risk.py               # Risk model capability contracts
│   │   │   │   │   ├── genai.py              # Narrative synthesis contracts
│   │   │   │   │   ├── knowledge.py          # Evidence guideline retrieval
│   │   │   │   │   └── audit.py              # HIPAA audit trail access
│   │   │   │   └── router.py                 # Central v1 API router
│   │   ├── clinical/
│   │   │   ├── domains.py                    # LOINC biomarkers & consensus guidelines
│   │   ├── core/
│   │   │   ├── config.py                     # Pydantic v2 settings & environment
│   │   │   ├── logging.py                    # Structured ISO-8601 JSON logging
│   │   │   ├── audit.py                      # Immutable SHA-256 audit engine
│   │   │   └── exceptions.py                 # Domain-specific clinical errors
│   │   ├── schemas/
│   │   │   ├── emr.py                        # FHIR R4 patient payload schemas
│   │   │   ├── risk.py                       # Risk score & confidence intervals
│   │   │   ├── genai.py                      # Narrative request/response contracts
│   │   │   ├── knowledge.py                  # Guideline RAG chunk schemas
│   │   │   └── health.py                     # Subsystem health schemas
│   │   ├── services/
│   │   │   ├── emr_ingestion.py              # Base EMR ingestion interface
│   │   │   ├── risk_engine.py                # Base predictive estimator interface
│   │   │   ├── genai_orchestrator.py         # Base LLM narrative synthesizer
│   │   │   └── knowledge_base.py             # Base RAG vector store interface
│   │   └── main.py                           # FastAPI application entrypoint
│   ├── tests/
│   │   └── test_health_and_domains.py        # Automated test suite
│   ├── pyproject.toml                        # Backend build & pytest configuration
│   ├── requirements.txt                      # Dependencies
│   └── .env.example                          # Environment template
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── clinical/
│   │   │   │   ├── DomainSpecCard.tsx        # Disease specifications & LOINC cards
│   │   │   │   ├── EMRValidationInspector.tsx# FHIR R4 schema live inspector
│   │   │   │   ├── RiskArchitectureView.tsx  # ML ensemble & model card matrix
│   │   │   │   ├── GenAIOrchestratorView.tsx # Dual-perspective synthesis view
│   │   │   │   ├── KnowledgeBaseView.tsx     # Evidence guideline repository
│   │   │   │   ├── SystemHealthCard.tsx      # Subsystem readiness probes
│   │   │   │   ├── AuditLogTable.tsx         # HIPAA audit log inspector
│   │   │   │   └── GovernanceModal.tsx       # CDS charter & compliance modal
│   │   │   ├── common/
│   │   │   │   ├── StatusBadge.tsx           # Clinical status indicators
│   │   │   │   └── ClinicalModal.tsx         # Accessible modal dialogue
│   │   │   └── layout/
│   │   │       ├── AppHeader.tsx             # Header with connectivity status
│   │   │       ├── AppSidebar.tsx            # Navigation & condition tags
│   │   │       ├── AppFooter.tsx             # Mandatory clinical notice
│   │   │       └── ClinicalBreadcrumbs.tsx   # Domain scope switcher
│   │   ├── lib/
│   │   │   └── api-client.ts                 # Typed fetch client with timeouts
│   │   ├── types/
│   │   │   └── clinical.ts                   # Strict TypeScript domain types
│   │   ├── App.tsx                           # Master application shell
│   │   ├── main.tsx                          # React 19 entrypoint
│   │   └── index.css                         # Tailwind CSS v4 design tokens
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docker/
│   ├── Dockerfile.backend                    # Multi-stage hardened Python image
│   ├── Dockerfile.frontend                   # Multi-stage Nginx SPA image
│   └── docker-compose.yml                    # Containerized stack orchestration
│
└── docs/
    ├── stack.md                              # Technology decision record
    └── architecture/
        ├── overview.md                       # System architecture & diagrams
        ├── clinical_domains.md               # 4 condition specifications & LOINC
        ├── data_flow.md                      # End-to-end data lifecycle
        ├── hipaa_security.md                 # HIPAA compliance & audit rules
        └── genai_governance.md               # FDA CDS boundary & GenAI safety
```

---

## Quickstart Guide

### 1. Backend Service
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* **Interactive API Documentation (Swagger)**: `http://localhost:8000/docs`
* **Health Check**: `http://localhost:8000/api/v1/health`

### 2. Run Backend Automated Tests
```bash
cd backend
.venv/bin/pytest tests/
```

### 3. Frontend Web Shell
```bash
cd frontend
npm install
npm run dev
```
* **Clinician Web Application**: `http://localhost:3000`

---

## Implementation Status (Step 1 Foundation)
* [x] Scalable, modular monorepo structure
* [x] Pydantic v2 schemas for FHIR R4 EMR ingestion & risk evaluation
* [x] FastAPI backend with structured JSON logging and HIPAA §164.312 audit logging
* [x] Registered clinical specifications for Diabetes, Cardiovascular, CKD, and Cancer
* [x] Abstract service interfaces for Ingestion, Predictive Models, GenAI, and RAG
* [x] Clean React 19 + TypeScript + Tailwind CSS application shell
* [x] Automated test suite passing with 100% success rate
* [x] Production Docker and Docker Compose definitions
* [ ] *Intentionally Deferred to Phase 2*: Model training cohorts, real EMR feature pipelines, and calibrated prediction weights.
* [ ] *Intentionally Deferred to Phase 3*: Live LLM API provider key integration and vector embeddings indexing.
# EMRs
