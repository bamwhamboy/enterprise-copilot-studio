import { API_BASE_URL } from "@/services/api-client";

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
}

/**
 * GET /health is a pure liveness check (deliberately no DB/Qdrant/Redis
 * dependency on the backend, so it stays meaningful even during a
 * downstream outage) -- called directly, without the JWT-attaching
 * apiClient, since it's unauthenticated on the backend and sits outside
 * /api/v1.
 */
export async function checkHealth(): Promise<{ ok: boolean; latencyMs: number; data?: HealthResponse }> {
  const healthUrl = API_BASE_URL.replace(/\/api\/v1\/?$/, "/health");
  const start = performance.now();
  try {
    const res = await fetch(healthUrl, { cache: "no-store" });
    const latencyMs = Math.round(performance.now() - start);
    if (!res.ok) return { ok: false, latencyMs };
    const data: HealthResponse = await res.json();
    return { ok: true, latencyMs, data };
  } catch {
    return { ok: false, latencyMs: Math.round(performance.now() - start) };
  }
}
