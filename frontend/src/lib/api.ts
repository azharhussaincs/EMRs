import type {
  HealthCheckResponse,
  DiseaseDomainRegistryEntry,
  EMRValidationResponse,
  EMRIngestionSuccessResponse,
  NormalizedPatientRecord,
  ClinicalValidationErrorItem,
  RiskAssessmentResult,
  ModelGovernanceCard,
  ClinicalNarrativeExplanation,
  EvidenceRetrievalResponse,
  EvidenceSourceRegistryEntry,
} from '@/types/clinical';

const PRIMARY_API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const FALLBACK_API_URL = 'http://localhost:8001/api/v1';

async function fetchFromApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const tryUrl = async (baseUrl: string) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options?.headers,
    };

    try {
      const res = await fetch(`${baseUrl}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeout);
      return res;
    } catch (err) {
      clearTimeout(timeout);
      throw err;
    }
  };

  // Try Primary (8000), then fallback (8001)
  let response: Response;
  try {
    response = await tryUrl(PRIMARY_API_URL);
  } catch {
    response = await tryUrl(FALLBACK_API_URL);
  }

  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    // Extract clinician-safe message without exposing stack traces
    const cleanMessage =
      (typeof errBody.detail === 'string' ? errBody.detail : null) ||
      (typeof errBody.message === 'string' ? errBody.message : null) ||
      `Clinical API request failed (${response.status})`;
    const error: Error & { status?: number; data?: unknown } = new Error(cleanMessage);
    error.status = response.status;
    error.data = errBody;
    throw error;
  }

  return response.json() as Promise<T>;
}

export async function fetchHealthStatus(): Promise<HealthCheckResponse> {
  return fetchFromApi<HealthCheckResponse>('/health');
}

export async function fetchClinicalDomains(): Promise<DiseaseDomainRegistryEntry[]> {
  return fetchFromApi<DiseaseDomainRegistryEntry[]>('/clinical/domains');
}

export async function fetchSampleFHIR(): Promise<Record<string, unknown>> {
  return fetchFromApi<Record<string, unknown>>('/emr/sample-fhir');
}

export async function validateEMRPayload(payload: unknown): Promise<EMRValidationResponse> {
  return fetchFromApi<EMRValidationResponse>('/emr/validate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function ingestEMRPayload(payload: unknown): Promise<EMRIngestionSuccessResponse> {
  return fetchFromApi<EMRIngestionSuccessResponse>('/emr/ingest', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchPatientRecord(patientId: string): Promise<NormalizedPatientRecord> {
  return fetchFromApi<NormalizedPatientRecord>(`/emr/patients/${patientId}`);
}

export async function fetchPatientDiabetesRisk(
  patientId: string
): Promise<RiskAssessmentResult> {
  return fetchFromApi<RiskAssessmentResult>(
    `/risk/patients/${encodeURIComponent(patientId)}/diabetes`
  );
}

export async function fetchDiabetesModelCard(): Promise<ModelGovernanceCard> {
  return fetchFromApi<ModelGovernanceCard>('/risk/models/diabetes');
}

export async function fetchPatientCardiovascularRisk(
  patientId: string
): Promise<RiskAssessmentResult> {
  return fetchFromApi<RiskAssessmentResult>(
    `/risk/patients/${encodeURIComponent(patientId)}/cardiovascular`
  );
}

export async function fetchCardiovascularModelCard(): Promise<ModelGovernanceCard> {
  return fetchFromApi<ModelGovernanceCard>('/risk/models/cardiovascular');
}

export async function generatePatientDiabetesNarrative(
  patientId: string
): Promise<ClinicalNarrativeExplanation> {
  return fetchFromApi<ClinicalNarrativeExplanation>(
    `/genai/narrative/patients/${encodeURIComponent(patientId)}/diabetes`,
    {
      method: 'POST',
    }
  );
}

export async function generatePatientCardiovascularNarrative(
  patientId: string
): Promise<ClinicalNarrativeExplanation> {
  return fetchFromApi<ClinicalNarrativeExplanation>(
    `/genai/narrative/patients/${encodeURIComponent(patientId)}/cardiovascular`,
    {
      method: 'POST',
    }
  );
}

export async function fetchPatientDiabetesEvidence(
  patientId?: string,
  category?: string
): Promise<EvidenceRetrievalResponse> {
  const params = new URLSearchParams();
  if (patientId) params.append('patient_id', patientId);
  if (category) params.append('category', category);
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  return fetchFromApi<EvidenceRetrievalResponse>(`/evidence/diabetes${queryStr}`);
}

export async function fetchPatientCardiovascularEvidence(
  patientId?: string,
  category?: string
): Promise<EvidenceRetrievalResponse> {
  const params = new URLSearchParams();
  if (patientId) params.append('patient_id', patientId);
  if (category) params.append('category', category);
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  return fetchFromApi<EvidenceRetrievalResponse>(`/evidence/cardiovascular${queryStr}`);
}

export async function fetchEvidenceSources(): Promise<EvidenceSourceRegistryEntry[]> {
  return fetchFromApi<EvidenceSourceRegistryEntry[]>('/evidence/sources');
}



