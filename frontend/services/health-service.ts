/**
 * Health service — API calls for health and system status endpoints.
 *
 * Separated from hooks for clean architecture:
 * services handle HTTP calls, hooks handle React state.
 */

import api from "@/lib/api";

/** Response from GET /api/health */
export interface HealthResponse {
  status: string;
  message: string;
}

/** Status of an individual subsystem */
export interface SubsystemStatus {
  name: string;
  status: string;
  message: string;
}

/** Response from GET /api/system-status */
export interface SystemStatusResponse {
  backend: SubsystemStatus;
  database: SubsystemStatus;
  ollama: SubsystemStatus;
  system_ready: boolean;
}

/**
 * Fetch basic health check.
 * GET /api/health
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/api/health");
  return data;
}

/**
 * Fetch full system status (backend, DB, Ollama).
 * GET /api/system-status
 */
export async function fetchSystemStatus(): Promise<SystemStatusResponse> {
  const { data } = await api.get<SystemStatusResponse>("/api/system-status");
  return data;
}
