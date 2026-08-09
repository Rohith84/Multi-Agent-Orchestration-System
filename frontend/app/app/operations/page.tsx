/**
 * Operations & System Health Dashboard Page.
 *
 * Features:
 * - Live Health, Readiness, and Liveness Probes
 * - Celery Worker status & Queue monitoring
 * - Redis Cache Statistics & Flush Cache control
 * - CPU & Memory resource usage tracking
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Activity,
  Server,
  Database,
  Cpu,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HardDrive,
  Trash2,
  Zap,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchReadinessProbe,
  fetchOperationsSummary,
  clearSystemCache,
  type ReadinessResponse,
  type OperationsSummaryResponse,
} from "@/services/operations-service";

export default function OperationsPage() {
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [opsSummary, setOpsSummary] = useState<OperationsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [readRes, opsRes] = await Promise.all([
        fetchReadinessProbe(),
        fetchOperationsSummary(),
      ]);
      setReadiness(readRes);
      setOpsSummary(opsRes);
    } catch (err) {
      console.error("Failed to load operations data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Auto refresh every 10s
    return () => clearInterval(interval);
  }, [loadData]);

  const handleClearCache = async () => {
    setActionLoading(true);
    try {
      await clearSystemCache();
      await loadData();
    } catch (err) {
      console.error("Failed to clear cache:", err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <main className="flex-1 p-6 sm:p-8 lg:p-12 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors mb-3"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Activity className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Operations & Health Platform</h1>
              <p className="text-sm text-zinc-400">
                System Probes • Celery Workers • Redis Caching • Resource Usage
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={() => loadData()}
            variant="outline"
            size="sm"
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh Probes
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 text-cyan-400 animate-spin" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Probes & Status Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Readiness Probe</span>
                <ShieldCheck className="h-4 w-4 text-cyan-400" />
              </div>
              <div className="flex items-center gap-2 mt-1">
                {readiness?.status === "ready" ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 text-sm font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 className="h-4 w-4" /> Ready (200 OK)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 text-sm font-bold rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
                    <XCircle className="h-4 w-4" /> Degraded
                  </span>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Celery Workers</span>
                <Server className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-1">
                {opsSummary?.workers.active_workers_count || 1} Active Worker
              </div>
              <p className="text-[11px] text-indigo-300 mt-1">Queue: workflows, indexing, tools</p>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">CPU & Memory</span>
                <Cpu className="h-4 w-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-1">
                {opsSummary?.memory_used_mb} MB
              </div>
              <p className="text-[11px] text-zinc-400 mt-1">CPU Load: {opsSummary?.cpu_usage_percentage}%</p>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Redis Cache Hit Ratio</span>
                <Zap className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-emerald-400 mt-1">
                {opsSummary?.cache.hit_ratio_percentage}%
              </div>
              <p className="text-[11px] text-zinc-400 mt-1">{opsSummary?.cache.hits} Hits / {opsSummary?.cache.misses} Misses</p>
            </div>
          </div>

          {/* Subsystem Health Table */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm space-y-4">
            <h3 className="text-sm font-semibold text-white">Subsystem Dependency Health</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-zinc-950/60 border border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Database className="h-5 w-5 text-indigo-400" />
                  <div>
                    <div className="text-xs font-semibold text-white">PostgreSQL Database</div>
                    <div className="text-[10px] text-zinc-500">Port 5432</div>
                  </div>
                </div>
                {readiness?.database ? (
                  <span className="text-xs font-bold text-emerald-400">Connected</span>
                ) : (
                  <span className="text-xs font-bold text-red-400">Disconnected</span>
                )}
              </div>

              <div className="p-4 rounded-lg bg-zinc-950/60 border border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Zap className="h-5 w-5 text-amber-400" />
                  <div>
                    <div className="text-xs font-semibold text-white">Redis Cache & Broker</div>
                    <div className="text-[10px] text-zinc-500">Port 6379</div>
                  </div>
                </div>
                {readiness?.redis ? (
                  <span className="text-xs font-bold text-emerald-400">Connected</span>
                ) : (
                  <span className="text-xs font-bold text-amber-400">Fallback Mode</span>
                )}
              </div>

              <div className="p-4 rounded-lg bg-zinc-950/60 border border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <HardDrive className="h-5 w-5 text-cyan-400" />
                  <div>
                    <div className="text-xs font-semibold text-white">ChromaDB Vectorstore</div>
                    <div className="text-[10px] text-zinc-500">Persistent Storage</div>
                  </div>
                </div>
                <span className="text-xs font-bold text-emerald-400">Active</span>
              </div>
            </div>
          </div>

          {/* Redis Cache Control */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" /> Redis Cache Management
              </h3>
              <p className="text-xs text-zinc-400 mt-1">
                Cache stores LLM responses, vector retrieval chunks, and prompt templates to accelerate workflow execution.
              </p>
            </div>

            <Button
              onClick={handleClearCache}
              disabled={actionLoading}
              variant="outline"
              size="sm"
              className="border-red-500/30 text-red-400 hover:bg-red-500/10 shrink-0"
            >
              <Trash2 className="h-4 w-4 mr-2" /> Flush Cache
            </Button>
          </div>
        </div>
      )}
    </main>
  );
}
