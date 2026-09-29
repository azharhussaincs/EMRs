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
