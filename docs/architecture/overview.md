# Architectural Overview

## Clinical Problem Statement
Electronic Medical Records (EMRs) store dense, high-dimensional longitudinal patient histories (laboratory test results, vital signs, medication changes, and physician progress notes). In traditional clinical workflows, physicians suffer cognitive overload synthesizing fragmented records across multiple chronic disease trajectories.

This platform provides an **auditable, evidence-grounded, multi-disease risk assessment system** that:
1. Ingests structured EMR records conforming to HL7 FHIR R4.
2. Derives calibrated clinical risk trajectories across 4 high-burden chronic conditions:
   * **Type 2 Diabetes Mellitus & Complications**
   * **Atherosclerotic Cardiovascular Disease (ASCVD) & Heart Failure**
   * **Chronic Kidney Disease (CKD) Progression**
   * **Oncology Early Detection & Malignancy Screening**
3. Uses Generative AI with strict clinical guardrails to synthesize dual-perspective rationales (Clinician Differential Logic and Patient Plain-Language Literacy Summaries).
4. Links all outputs to peer-reviewed consensus clinical practice guidelines (ADA, ACC/AHA, KDIGO, NCCN).

---

## Component Architecture

```
                  +----------------------------------------------+
                  |         Clinician Workstation / EMR          |
                  |     (React 19 + TypeScript + Tailwind)       |
                  +----------------------+-----------------------+
                                         |
                                         | HTTPS (JSON / REST API)
                                         v
                  +----------------------------------------------+
                  |           API Gateway & Core Router          |
                  |             FastAPI (Python 3.10)            |
                  +----------------------+-----------------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
+------------------+           +-------------------+           +-------------------+
|  EMR Ingestion   |           |    HIPAA Audit    |           | Clinical Domain   |
|     Gateway      |           |   Trail Engine    |           |     Registry      |
|  (FHIR R4 / JSON)|           | (§164.312 SHA-256)|           |  (4 Core Diseases)|
+--------+---------+           +-------------------+           +---------+---------+
         |                                                               |
         +-------------------------------+-------------------------------+
                                         |
                                         v
                   +-------------------------------------------+
                   |       Service Layer (Abstract Base)       |
                   |                                           |
                   |  1. BaseEMRIngestionService               |
                   |  2. BaseRiskAssessmentEngine              |
                   |  3. BaseClinicalNarrativeGenerator        |
                   |  4. BaseClinicalKnowledgeBase             |
                   +---------------------+---------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
+-------------------------------+               +----------------------------------+
|   Predictive Risk Pipelines   |               | Generative AI Orchestrator & RAG |
|    (To be wired in Phase 2)   |               |     (To be wired in Phase 3)     |
| • XGBoost / Cox Hazards       |               | • LLM Context Assembler          |
| • Platt / Beta Calibration    |               | • ADA/ACC/KDIGO/NCCN Grounding   |
| • TreeSHAP Biomarker Weights  |               | • Dual Audience Summarizer       |
+-------------------------------+               +----------------------------------+
```

---

## Modularity & Extensibility
The platform uses the **Dependency Inversion Principle**:
* Every subsystem communicates through abstract interfaces defined in `backend/app/services/`.
* New disease areas (e.g. Alzheimer's disease, COPD, Autoimmune conditions) can be introduced simply by declaring an entry in `backend/app/clinical/domains.py` and implementing the corresponding feature extractor.
* AI models can be updated, compared, or ensembled without modifying the API layer or the frontend presentation.
