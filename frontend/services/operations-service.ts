/**
 * Operations & System Health Service — API client for probes, system metrics, worker status, and cache management.
 */

import api from "@/lib/api";

export interface ReadinessResponse {
  status: "ready" | "not_ready";
  database: boolean;
  redis: boolean;
}

export interface OperationsSummaryResponse {
  status: string;
  cpu_usage_percentage: number;
  memory_used_mb: number;
  workers: {
    status: string;
    active_workers_count: number;
  };
  queues: Record<string, number>;
  cache: {
    hits: number;
    misses: number;
    total_requests: number;
    hit_ratio_percentage: number;
    fallback_keys_count: number;
  };
}

/**
 * Fetch readiness status probe.
 * GET /api/readiness
 */
export async function fetchReadinessProbe(): Promise<ReadinessResponse> {
  try {
    const { data } = await api.get<ReadinessResponse>("/api/readiness");
    return data;
  } catch (err: any) {
    return {
      status: "not_ready",
      database: false,
      redis: false,
    };
  }
}

/**
 * Fetch operations system summary.
 * GET /api/operations/system
 */
export async function fetchOperationsSummary(): Promise<OperationsSummaryResponse> {
  const { data } = await api.get<OperationsSummaryResponse>("/api/operations/system");
  return data;
}

/**
 * Flush Redis cache.
 * POST /api/operations/cache/clear
 */
export async function clearSystemCache(): Promise<{ status: string; message: string }> {
  const { data } = await api.post<{ status: string; message: string }>("/api/operations/cache/clear");
  return data;
}
