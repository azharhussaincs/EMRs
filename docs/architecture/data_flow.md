# Clinical Data Flow & Ingestion Lifecycle

```
[Electronic Medical Record / EHR System]
                 |
                 | (HL7 FHIR R4 Bundle / JSON Payload)
                 v
[1. Ingestion Boundary & Schema Validator]
  * Validates JSON schema against Pydantic FHIR models
  * Verifies LOINC coding syntax and ICD-10 formatting
  * Strips Direct Identifiers (De-identification & Pseudonymization)
                 |
                 +-----> [HIPAA Immutable Audit Trail]
                 |       (Records Event ID, Action, Timestamp, SHA-256 Digest)
                 v
[2. Clinical Feature Derivation Engine]
  * Extracts longitudinal biomarker sequences (e.g. HbA1c trajectory over 24 months)
  * Computes temporal moving averages, rate of change (eGFR slope)
  * Assembles domain-specific feature vector
                 |
                 v
[3. Calibrated Risk Prediction Ensemble]
  * Evaluates multi-disease risk models (Diabetes, ASCVD, CKD, Oncology)
  * Calculates calibrated empirical probability (0.0 to 1.0)
  * Determines 95% confidence intervals and SHAP attribution weights
                 |
                 v
[4. Generative AI Context Assembler & RAG]
  * Retrieves relevant consensus clinical guidelines (ADA, ACC, KDIGO, NCCN)
  * Formulates prompt with strict evidence grounding context and ZERO PHI
  * Enforces dual-perspective synthesis (Physician differential vs Patient plain-language)
                 |
                 v
[5. Clinician Decision Support Interface]
  * Displays risk trajectory with confidence bounds
  * Presents interactive biomarker impact cards
  * Requires explicit clinician review and verification before EHR write-back
```
