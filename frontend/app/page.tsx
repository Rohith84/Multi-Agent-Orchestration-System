/**
 * Dashboard page — main entry point of the application.
 *
 * Displays system health status with live data from the backend:
 * - Backend Status (live)
 * - Database Status (live)
 * - Ollama Status (live check, expected to be disconnected initially)
 * - System Ready (derived from all subsystems)
 *
 * Uses React Query for data fetching with loading and error states.
 */

"use client";

import { DashboardHeader } from "@/components/dashboard-header";
import { StatusCard, type StatusType } from "@/components/status-card";
import { useSystemStatus } from "@/hooks/use-system-status";
import { Button } from "@/components/ui/button";
import { RefreshCw, AlertTriangle, Shield } from "lucide-react";

export default function DashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useSystemStatus();

  // Derive status types from API response
  const getSubsystemStatus = (status?: string): StatusType => {
    if (isLoading) return "loading";
    if (isError) return "disconnected";
    if (!status) return "placeholder";
    return status === "connected" ? "connected" : "disconnected";
  };

  const getSystemReadyStatus = (): StatusType => {
    if (isLoading) return "loading";
    if (isError) return "disconnected";
    if (!data) return "placeholder";
    return data.system_ready ? "connected" : "disconnected";
  };

  return (
    <main className="flex-1 p-6 sm:p-8 lg:p-12 max-w-7xl mx-auto w-full">
      <DashboardHeader />

      {/* Error Banner */}
      {isError && (
        <div
          id="error-banner"
          className="mb-8 flex items-center gap-4 rounded-xl border border-red-500/20 bg-red-500/10 p-4 backdrop-blur-sm"
        >
          <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-400">
              Connection Error
            </p>
            <p className="text-xs text-red-400/70 mt-1">
              {error?.message || "Unable to reach the backend server."}
              {" "}Make sure the backend is running on{" "}
              <code className="text-red-300">localhost:8000</code>.
            </p>
          </div>
          <Button
            id="retry-button"
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="border-red-500/30 text-red-400 hover:bg-red-500/20 hover:text-red-300"
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isFetching ? "animate-spin" : ""}`}
            />
            Retry
          </Button>
        </div>
      )}

      {/* Success Banner */}
      {data && !isError && (
        <div
          id="success-banner"
          className="mb-8 flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 backdrop-blur-sm animate-in fade-in duration-500"
        >
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <p className="text-sm font-medium text-emerald-400">
            Backend Connected ✅
          </p>
        </div>
      )}

      {/* Status Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          id="backend-status"
          title="Backend Status"
          status={getSubsystemStatus(data?.backend?.status)}
          message={
            isError
              ? "Backend is unreachable"
              : data?.backend?.message || "Checking backend..."
          }
        />

        <StatusCard
          id="database-status"
          title="Database Status"
          status={getSubsystemStatus(data?.database?.status)}
          message={
            isError
              ? "Cannot determine database status"
              : data?.database?.message || "Checking database..."
          }
        />

        <StatusCard
          id="ollama-status"
          title="Ollama Status"
          status={
            isLoading
              ? "loading"
              : isError
                ? "placeholder"
                : getSubsystemStatus(data?.ollama?.status)
          }
          message={
            isError
              ? "Ollama check pending"
              : data?.ollama?.message || "Checking Ollama..."
          }
        />

        <StatusCard
          id="system-ready"
          title="System Ready"
          status={getSystemReadyStatus()}
          message={
            isError
              ? "System is not ready"
              : data?.system_ready
                ? "All systems operational"
                : data
                  ? "Some services are unavailable"
                  : "Checking system..."
          }
          icon={Shield}
        />
      </div>

      {/* Footer info */}
      <div className="mt-12 text-center">
        <p className="text-xs text-zinc-600">
          Auto-refreshing every 30 seconds •{" "}
          <button
            onClick={() => refetch()}
            className="text-zinc-500 hover:text-zinc-400 underline underline-offset-2 transition-colors"
          >
            Refresh now
          </button>
        </p>
      </div>
    </main>
  );
}
