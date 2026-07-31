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

import Link from "next/link";
import { DashboardHeader } from "@/components/dashboard-header";
import { StatusCard, type StatusType } from "@/components/status-card";
import { useSystemStatus } from "@/hooks/use-system-status";
import { Button } from "@/components/ui/button";
import { RefreshCw, AlertTriangle, Shield, MessageSquare, FileText, Wrench, Layers } from "lucide-react";

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
              {error?.message || "Unable to reach the backend server."}{" "}
              Make sure the backend is running on{" "}
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

      {/* AI Assistant Card */}
      <div className="mt-10">
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <Link href="/chat" className="group">
            <div className="relative overflow-hidden rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 to-blue-500/10 p-6 backdrop-blur-sm transition-all duration-300 hover:scale-[1.02] hover:border-violet-500/40 hover:shadow-lg hover:shadow-violet-500/10">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shadow-lg shadow-violet-500/20 group-hover:shadow-violet-500/30 transition-shadow">
                  <MessageSquare className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white group-hover:text-violet-300 transition-colors">
                    AI Assistant
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Chat with the AI • Code, debug, explore
                  </p>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-violet-500/5 to-transparent rounded-bl-full" />
            </div>
          </Link>

          <Link href="/knowledge" className="group">
            <div className="relative overflow-hidden rounded-xl border border-blue-500/20 bg-gradient-to-br from-blue-500/10 to-emerald-500/10 p-6 backdrop-blur-sm transition-all duration-300 hover:scale-[1.02] hover:border-blue-500/40 hover:shadow-lg hover:shadow-blue-500/10">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/20 group-hover:shadow-blue-500/30 transition-shadow">
                  <FileText className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white group-hover:text-blue-300 transition-colors">
                    Knowledge Base
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Manage files • Re-index search vectors
                  </p>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-blue-500/5 to-transparent rounded-bl-full" />
            </div>
          </Link>

          <Link href="/tools" className="group">
            <div className="relative overflow-hidden rounded-xl border border-orange-500/20 bg-gradient-to-br from-orange-500/10 to-amber-500/10 p-6 backdrop-blur-sm transition-all duration-300 hover:scale-[1.02] hover:border-orange-500/40 hover:shadow-lg hover:shadow-orange-500/10">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-orange-600 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20 group-hover:shadow-orange-500/30 transition-shadow">
                  <Wrench className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white group-hover:text-orange-300 transition-colors">
                    Tool Center
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    MCP Tools • Execute & Monitor
                  </p>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-orange-500/5 to-transparent rounded-bl-full" />
            </div>
          </Link>

          <Link href="/workflows" className="group">
            <div className="relative overflow-hidden rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-violet-500/10 p-6 backdrop-blur-sm transition-all duration-300 hover:scale-[1.02] hover:border-indigo-500/40 hover:shadow-lg hover:shadow-indigo-500/10">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/30 transition-shadow">
                  <Layers className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white group-hover:text-indigo-300 transition-colors">
                    Workflows
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    HITL Approvals • Checkpoints
                  </p>
                </div>
              </div>
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-indigo-500/5 to-transparent rounded-bl-full" />
            </div>
          </Link>
        </div>
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
