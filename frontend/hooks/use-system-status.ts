/**
 * React Query hook for the /api/system-status endpoint.
 *
 * Fetches aggregated status of all subsystems.
 * Polls every 30 seconds.
 */

import { useQuery } from "@tanstack/react-query";
import {
  fetchSystemStatus,
  type SystemStatusResponse,
} from "@/services/health-service";

export function useSystemStatus() {
  return useQuery<SystemStatusResponse, Error>({
    queryKey: ["system-status"],
    queryFn: fetchSystemStatus,
    refetchInterval: 30000,
    retry: 2,
    staleTime: 10000,
  });
}
