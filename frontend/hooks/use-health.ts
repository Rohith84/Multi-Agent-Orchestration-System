/**
 * React Query hook for the /api/health endpoint.
 *
 * Polls every 30 seconds to keep the dashboard status live.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchHealth, type HealthResponse } from "@/services/health-service";

export function useHealth() {
  return useQuery<HealthResponse, Error>({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30000, // Poll every 30s
    retry: 2,
    staleTime: 10000,
  });
}
