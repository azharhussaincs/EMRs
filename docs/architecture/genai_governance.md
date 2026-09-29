# Generative AI Governance & Clinical Safety Framework

## 1. Regulatory Boundary: FDA Clinical Decision Support (CDS) Guidance
Under Section 520(o)(1)(E) of the Federal Food, Drug, and Cosmetic Act (FD&C Act) as amended by the 21st Century Cures Act:
* The platform provides recommendations for prevention and disease trajectory management.
* The platform enables the healthcare provider to independently review the basis for the recommendations (via transparent biomarker contribution weights, model cards, and direct guideline citations).
* **The software does NOT replace clinical judgment or issue automated diagnostic orders.**

## 2. Hallucination Mitigation & Deterministic Evidence Grounding
Generative AI models (LLMs) cannot be permitted to generate open-ended medical claims without verification. The platform enforces a multi-tier guardrail:
1. **Grounding-Only Context Assembly**: All clinical recommendations must be cited directly from consensus clinical guidelines retrieved from the knowledge store (ADA, ACC/AHA, KDIGO, NCCN).
2. **Automated Factuality Assertion**: Model output is post-processed to confirm that recommended drugs, dosages, and diagnostic tests exist within the injected guideline citations.
3. **Structured Pydantic Contract**: Outputs adhere to strict schemas (`ClinicalNarrativeResponse`) rather than free-form text strings.

## 3. Dual-Perspective Tailoring
* **Physician Perspective**: Detailed pathophysiological differential rationale, clinical pharmacology guidance, formal evidence grading (Level A, Class I), and suggested surveillance intervals.
* **Patient Perspective**: Clear, empathetic, non-alarmist health literacy summary (Flesch-Kincaid grade level ≤ 7), key lifestyle modifications, and focused questions for the patient to discuss with their clinician.

## 4. Physician-in-the-Loop Sign-off Mandate
* No AI-generated summary or risk score is permanently entered into the patient record or communicated to the patient without an explicit clinician digital sign-off and review action.
