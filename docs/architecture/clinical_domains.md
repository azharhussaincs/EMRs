# Clinical Domains & Ontology Specifications

## 1. Type 2 Diabetes Mellitus & Complications
* **ICD-10-CM Family**: `E11` (Type 2 diabetes mellitus), `E11.9` (without complications), `E11.22` (diabetic chronic kidney disease), `E11.65` (hyperglycemia)
* **SNOMED-CT Concept**: `44054006`
* **Target Prediction Horizons**: 3-year, 5-year, 10-year
* **Primary Biomarkers & Vitals**:
  * Hemoglobin A1c (LOINC: `4548-4`, Unit: `%`)
  * Fasting Plasma Glucose (LOINC: `1558-6`, Unit: `mg/dL`)
  * Body Mass Index (LOINC: `39156-5`, Unit: `kg/m²`)
* **Consensus Guideline Baseline**:
  * *American Diabetes Association (ADA)* Standards of Care in Diabetes (2024), Level A Evidence.
  * Emphasizes glycemic variability trajectory, cardiorenal protection, and early initiation of organ-protective pharmacotherapy (SGLT2 inhibitors and GLP-1 receptor agonists).

---

## 2. Atherosclerotic Cardiovascular Disease (ASCVD) & Heart Failure
* **ICD-10-CM Family**: `I25.10` (Atherosclerotic heart disease), `I21.9` (Acute myocardial infarction), `I50.9` (Heart failure), `I10` (Essential hypertension)
* **SNOMED-CT Concept**: `49436004`
* **Target Prediction Horizons**: 5-year, 10-year, Lifetime
* **Primary Biomarkers & Vitals**:
  * Systolic Blood Pressure (LOINC: `8480-6`, Unit: `mmHg`)
  * Total Serum Cholesterol (LOINC: `2093-3`, Unit: `mg/dL`)
  * High-Density Lipoprotein (HDL) Cholesterol (LOINC: `2085-9`, Unit: `mg/dL`)
  * High-Sensitivity Cardiac Troponin (LOINC: `89579-7`, Unit: `ng/L`)
* **Consensus Guideline Baseline**:
  * *American College of Cardiology / American Heart Association (ACC/AHA)* Guideline on the Primary Prevention of Cardiovascular Disease (2019), Class I / Level A.
  * Standardizes 10-year primary event risk (pooled cohort equations) and statin benefit thresholds.

---

## 3. Chronic Kidney Disease (CKD) Progression
* **ICD-10-CM Family**: `N18.1` (Stage 1) through `N18.6` (End Stage Renal Disease)
* **SNOMED-CT Concept**: `709044004`
* **Target Prediction Horizons**: 1-year, 2-year, 5-year
* **Primary Biomarkers & Vitals**:
  * Estimated Glomerular Filtration Rate (eGFR, CKD-EPI formula, LOINC: `33914-3`, Unit: `mL/min/1.73m²`)
  * Urine Albumin-to-Creatinine Ratio (uACR, LOINC: `14959-1`, Unit: `mg/g`)
  * Serum Creatinine (LOINC: `2160-0`, Unit: `mg/dL`)
* **Consensus Guideline Baseline**:
  * *Kidney Disease: Improving Global Outcomes (KDIGO)* Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease (2024), Grade 1A.
  * Utilizes CGA staging (Cause, GFR category G1-G5, Albuminuria category A1-A3) to calculate composite renal failure trajectory.

---

## 4. Oncology Early Detection & Malignancy Screening
* **ICD-10-CM Family**: `C00-D49` (Neoplasms), `C34.90` (Bronchus and lung), `C50.919` (Breast), `C18.9` (Colon)
* **SNOMED-CT Concept**: `363346000`
* **Target Prediction Horizons**: 1-year, 5-year
* **Primary Biomarkers & Vitals**:
  * Carcinoembryonic Antigen (CEA, LOINC: `2039-6`, Unit: `ng/mL`)
  * Prostate-Specific Antigen (PSA, LOINC: `2857-1`, Unit: `ng/mL`)
  * Cancer Antigen 125 (CA-125, LOINC: `10334-1`, Unit: `U/mL`)
* **Consensus Guideline Baseline**:
  * *National Comprehensive Cancer Network (NCCN)* Clinical Practice Guidelines in Oncology: Detection, Prevention, & Risk Assessment (2024), Category 1.
  * Integrates age-stratified screening protocols, family hereditary history, and biomarker deviations.
