export type ClinicalDomain =
  | 'diabetes'
  | 'cardiovascular'
  | 'chronic_kidney_disease'
  | 'cancer';

export type WorkflowStepId =
  | 'emr'
  | 'clinical_info'
  | 'risk_assessment'
  | 'ai_explanation'
  | 'evidence';

export interface WorkflowStep {
  id: WorkflowStepId;
  stepNumber: number;
  label: string;
  summary: string;
  detail: string;
}

export interface ClinicalBiomarkerSpec {
  name: string;
  loinc_code?: string;
  unit: string;
  description: string;
}

export interface ClinicalGuidelineReference {
  organization: string;
  title: string;
  edition_year: number;
  evidence_level: string;
  url?: string;
}

export interface DiseaseDomainRegistryEntry {
  domain: ClinicalDomain;
  display_name: string;
  icd10_family: string[];
  snomed_ct_concept?: string;
  description: string;
  primary_biomarkers: ClinicalBiomarkerSpec[];
  consensus_guidelines: ClinicalGuidelineReference[];
  target_risk_horizons: string[];
}

export interface SubsystemStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unavailable';
  details: string;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
  active_clinical_domains: ClinicalDomain[];
  subsystems: Record<string, SubsystemStatus>;
}

// --- EMR Validation & Normalization Types ---
export interface ClinicalValidationErrorItem {
  field: string;
  issue: string;
  code: string;
  observed_value?: unknown;
  acceptable_range?: string;
}

export interface EMRValidationResponse {
  valid: boolean;
  patient_id?: string;
  errors: ClinicalValidationErrorItem[];
  warnings: string[];
  observations_count: number;
  conditions_count: number;
  medications_count: number;
  clinical_notes_count: number;
  message: string;
}

export interface NormalizedBiomarkerPoint {
  observation_id: string;
  biomarker_key: string;
  standard_name: string;
  effective_datetime: string;
  value: number;
  unit: string;
  loinc_code?: string;
  reference_range_low?: number;
  reference_range_high?: number;
}

export interface NormalizedCondition {
  condition_id: string;
  icd10_code: string;
  display_name: string;
  clinical_status: string;
  recorded_date?: string;
}

export interface NormalizedMedication {
  medication_id: string;
  display_name: string;
  rxnorm_code?: string;
  dosage_instruction?: string;
  status: string;
}

export interface NormalizedClinicalNote {
  note_id: string;
  note_type: string;
  created_at: string;
  author_specialty?: string;
  text_preview: string;
}

export interface NormalizedPatientRecord {
  patient_id: string;
  gender?: string;
  birth_date?: string;
  age_years?: number;
  longitudinal_biomarkers: Record<string, NormalizedBiomarkerPoint[]>;
  conditions: NormalizedCondition[];
  medications: NormalizedMedication[];
  clinical_notes: NormalizedClinicalNote[];
  clinical_domain_readiness: {
    diabetes: boolean;
    cardiovascular: boolean;
    chronic_kidney_disease: boolean;
    cancer: boolean;
  };
  total_biomarker_measurements: number;
  earliest_record_date?: string;
  latest_record_date?: string;
}

export interface EMRIngestionSuccessResponse {
  status: string;
  ingestion_id: string;
  audit_event_id: string;
  patient_record: NormalizedPatientRecord;
  received_at: string;
}

// --- Step 5 & 6 Disease Risk Stratification & Model Governance Types ---

export type DataSufficiencyStatus =
  | 'sufficient_data'
  | 'insufficient_data'
  | 'unavailable_feature';

export type CalibrationStatus =
  | 'not_calibrated'
  | 'calibrated'
  | 'insufficient_model';

export interface ConfidenceInterval {
  low?: number | null;
  high?: number | null;
  confidence_level: number;
}

export interface UsedFeatureValue {
  feature_name: string;
  value?: number | null;
  unit?: string | null;
  source_timestamp?: string | null;
  description: string;
}

export interface RiskAssessmentResult {
  assessment_id: string;
  patient_id: string;
  assessed_at: string;
  domain: ClinicalDomain;
  estimator_id: string;
  estimator_version: string;
  data_sufficiency: DataSufficiencyStatus;
  calibration_status: CalibrationStatus;
  risk_estimate?: number | null;
  confidence_interval?: ConfidenceInterval | null;
  features_used: Record<string, UsedFeatureValue>;
  unavailable_inputs: string[];
  limitations: string[];
  disclaimer: string;
}

export interface ModelGovernanceCard {
  estimator_id: string;
  version: string;
  domain: string;
  target: string;
  input_features: string[];
  calibration_status: string;
  assumptions: string;
  disclaimer: string;
  status?: string;
}

export interface ClinicalNarrativeExplanation {
  narrative_id: string;
  context_id: string;
  patient_id: string;
  assessment_id: string;
  domain: ClinicalDomain;
  summary: string;
  observed_trajectory: string;
  data_limitations: string;
  statistical_calibration_status: string;
  disclaimer: string;
  provider: string;
  model_name: string;
  generated_at: string;
}

// --- Step 10 & 11 Clinical Evidence & Guideline Retrieval Types ---

export type EvidenceStatus = 'verified' | 'unavailable';

export type EvidenceDomainCategory =
  | 'hba1c_monitoring'
  | 'glycemic_trajectory_assessment'
  | 'diabetes_classification_context'
  | 'diabetes_ckd_intersection'
  | 'cardiovascular_risk_expansion';

export interface EvidenceSourceRegistryEntry {
  source_id: string;
  organization: string;
  title: string;
  edition_year: number;
  guideline_identifier?: string | null;
  official_url: string;
  domain: ClinicalDomain;
  publication_status: string;
  retrieval_date: string;
  citation_metadata: string;
}

export interface ClinicalEvidenceReference {
  evidence_id: string;
  source_id: string;
  organization: string;
  guideline_title: string;
  publication_version: string;
  section_chapter?: string | null;
  recommendation_identifier?: string | null;
  citation_text: string;
  official_url: string;
  evidence_status: EvidenceStatus;
  domain_category: EvidenceDomainCategory;
  scope_description: string;
  retrieved_at: string;
}

export interface EvidenceRetrievalResponse {
  domain: string;
  query_category?: string | null;
  total_references: number;
  provider_id: string;
  references: ClinicalEvidenceReference[];
  retrieved_at: string;
  disclaimer: string;
}


