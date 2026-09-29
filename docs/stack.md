# Technology Stack Decision Record

## 1. Backend Core & API Layer
* **Language**: Python 3.10+
  * *Rationale*: Dominant language ecosystem for clinical AI/ML, healthcare informatics (PyFHIR, MedCAT, BioSentVec), and modern LLM orchestration.
* **Framework**: FastAPI (>= 0.115.0)
  * *Rationale*: Native asynchronous performance (ASGI via Uvicorn/uvloop), automatic OpenAPI/Swagger interactive documentation, built-in validation with Pydantic v2, and lightweight container footprint.
* **Data Validation & Typing**: Pydantic v2 (>= 2.8.0)
  * *Rationale*: Rust-backed high-speed validation of deeply nested clinical payloads (FHIR R4 resources, longitudinal lab measurements), strict schema typing, and zero runtime type degradation.
* **Audit & Logging**: Custom JSON Formatter with UTC ISO-8601 timestamps and SHA-256 integrity hashing.
  * *Rationale*: Compliance with HIPAA Security Rule §164.312(b) Audit Controls.

## 2. Frontend Application Shell
* **Framework & Runtime**: Next.js 16 (App Router) + React 19 + TypeScript (Strict Mode)
  * *Rationale*: Production standard for healthcare web applications, modular page and component organization, static rendering efficiency, and seamless typed REST client integration with FastAPI.
* **Styling & Design System**: Tailwind CSS v4
  * *Rationale*: High-contrast WCAG 2.1 AA accessible healthcare color token system (Slate foundations, medical teal/cyan accents, and clear clinical status hierarchy) without cluttered dashboards.
* **Iconography**: Lucide React
  * *Rationale*: Clean, standardized, clinical-grade glyphs with consistent optical weights.

## 3. Clinical Informatics & Ontologies
* **Laboratory & Physiological Observations**: LOINC (Logical Observation Identifiers Names and Codes)
* **Diagnoses & Conditions**: ICD-10-CM & SNOMED-CT (Systematized Nomenclature of Medicine - Clinical Terms)
* **Pharmacotherapy**: RxNorm
* **Interoperability Standard**: HL7 FHIR Release 4 (R4) resource representation

## 4. Modeling & Generative AI Architecture (Future Phases)
* **Predictive Estimators**: Scikit-learn, XGBoost, Cox Proportional Hazards, PyTorch (calibrated via Platt scaling or isotonic regression)
* **Generative AI Orchestrator**: Pluggable provider abstraction (Gemini / Anthropic / Local vLLM) with strict prompt watermarking and mandatory evidence-grounding guardrails
* **Clinical Knowledge Base (RAG)**: Hybrid retrieval (BM25 lexical + dense vector embeddings) backed by pgvector or Qdrant for consensus guideline citation

## 5. Deployment & Containerization
* **Containerization**: Multi-stage unprivileged Docker containers (`Dockerfile.backend`, `Dockerfile.frontend`)
* **Orchestration**: Docker Compose with health probe dependencies and isolated internal networks.
