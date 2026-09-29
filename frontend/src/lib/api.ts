import type { HealthCheckResponse, DiseaseDomainRegistryEntry } from '@/types/clinical';

const PRIMARY_API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const FALLBACK_API_URL = 'http://localhost:8001/api/v1';

async function fetchFromApi<T>(endpoint: string): Promise<T> {
  // Try primary API URL first
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    const res = await fetch(`${PRIMARY_API_URL}${endpoint}`, {
      cache: 'no-store',
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (res.ok) {
      return (await res.json()) as T;
    }
  } catch {
    // Primary failed or timed out, attempt secondary port
  }

  // Attempt fallback port (8001)
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);
  try {
    const res = await fetch(`${FALLBACK_API_URL}${endpoint}`, {
      cache: 'no-store',
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (res.ok) {
      return (await res.json()) as T;
    }
    throw new Error(`API returned HTTP ${res.status}`);
  } catch (err) {
    clearTimeout(timeout);
    throw err;
  }
}

export async function fetchHealthStatus(): Promise<HealthCheckResponse> {
  return fetchFromApi<HealthCheckResponse>('/health');
}

export async function fetchClinicalDomains(): Promise<DiseaseDomainRegistryEntry[]> {
  return fetchFromApi<DiseaseDomainRegistryEntry[]>('/clinical/domains');
}
