// Full Analytics implementation copied from legacy file
/**
 * Analytics & LLMOps Dashboard Page.
 *
 * Features:
 * - System Performance KPIs (Overall Score, Tokens, Latency, Success Rate)
 * - LLM Model Comparisons (Speed, Tokens, Quality, Call volume)
 * - MCP Tool & RAG Retrieval Statistics
 * - Prompt Registry Manager (Version templates, create, activate)
 * - Export Reports in JSON or CSV formats
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  Brain,
  Zap,
  Clock,
  CheckCircle2,
  FileText,
  Download,
  Wrench,
  Database,
  Layers,
  Sparkles,
  RefreshCw,
  Plus,
  Check,
  Loader2,
  Sliders,
  Code2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchDashboardAnalytics,
  exportAnalyticsReport,
  fetchPromptVersions,
  createPromptVersion,
  activatePromptVersion,
  type DashboardAnalyticsResponse,
  type PromptVersion,
} from "@/services/analytics-service";

type ActiveTab = "overview" | "models" | "tools_rag" | "prompts";

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");
  const [analytics, setAnalytics] = useState<DashboardAnalyticsResponse | null>(null);
  const [prompts, setPrompts] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // New Prompt Form
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [agentName, setAgentName] = useState("coder");
  const [version, setVersion] = useState("v2.0");
  const [template, setTemplate] = useState("");
  const [description, setDescription] = useState("");

  const loadData = useCallback(async () => {
    try {
      const [data, promptList] = await Promise.all([
        fetchDashboardAnalytics(),
        fetchPromptVersions(),
      ]);
      setAnalytics(data);
      setPrompts(promptList);
    } catch (err) {
      console.error("Failed to load analytics data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExport = async (format: "json" | "csv") => {
    try {
      const report = await exportAnalyticsReport(format);
      const blob = new Blob([report], {
        type: format === "csv" ? "text/csv" : "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `observability_report_${Date.now()}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export report:", err);
    }
  };

  const handleCreatePrompt = async () => {
    if (!template) return;
    setActionLoading(true);
    try {
      await createPromptVersion({
        agent_name: agentName,
        version: version,
        template: template,
        description: description,
      });
      setShowPromptModal(false);
      setTemplate("");
      setDescription("");
      await loadData();
    } catch (err) {
      console.error("Failed to create prompt version:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleActivatePrompt = async (id: string) => {
    setActionLoading(true);
    try {
      await activatePromptVersion(id);
      await loadData();
    } catch (err) {
      console.error("Failed to activate prompt:", err);
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
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <BarChart3 className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Analytics & LLMOps Platform</h1>
              <p className="text-sm text-zinc-400">
                Evaluation Metrics • Token & Latency Analytics • Prompt Registry
              </p>
            </div>
          </div>
        </div>

        {/* Export Controls */}
        <div className="flex gap-3">
          <Button
            onClick={() => handleExport("json")}
            variant="outline"
            size="sm"
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            <Download className="h-4 w-4 mr-2" /> Export JSON
          </Button>
          <Button
            onClick={() => handleExport("csv")}
            size="sm"
            className="bg-gradient-to-r from-emerald-600 to-teal-500 text-white font-medium shadow-md shadow-emerald-500/20"
          >
            <Download className="h-4 w-4 mr-2" /> Export CSV
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-zinc-800 pb-3">
        {[{ id: "overview", label: "Overview & KPIs", icon: BarChart3 }, { id: "models", label: "Model Comparison", icon: Brain }, { id: "tools_rag", label: "MCP & RAG Stats", icon: Wrench }, { id: "prompts", label: "Prompt Registry", icon: Code2 }].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ActiveTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800/40"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 text-emerald-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* Overview Tab */}
          {activeTab === "overview" && analytics && (
            <div className="space-y-6">
              {/* KPI Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
                  <div className="flex items-center justify-between text-zinc-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Quality Score</span>
                    <Sparkles className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {analytics.overall_quality_score} <span className="text-sm font-normal text-zinc-500">/ 10</span>
                  </div>
                  <p className="text-[11px] text-emerald-400 mt-1">LLM-as-a-Judge Evaluation</p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
                  <div className="flex items-center justify-between text-zinc-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Total Tokens</span>
                    <Zap className="h-4 w-4 text-amber-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {analytics.total_tokens_consumed.toLocaleString()}
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-1">Estimated input + output tokens</p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
                  <div className="flex items-center justify-between text-zinc-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Avg Latency</span>
                    <Clock className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {analytics.avg_workflow_latency}s
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-1">Per completed workflow</p>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm">
                  <div className="flex items-center justify-between text-zinc-400 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wider">Success Rate</span>
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="text-3xl font-extrabold text-white">
                    {analytics.success_rate_percentage}%
                  </div>
                  <p className="text-[11px] text-emerald-400 mt-1">{analytics.total_workflows_executed} Workflows Executed</p>
                </div>
              </div>

              {/* Recent Agent Executions Table */}
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm">
                <h3 className="text-sm font-semibold text-white mb-4">Recent Agent Performance Traces</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-zinc-800 text-zinc-500 uppercase tracking-wider">
                        <th className="pb-3">Agent</th>
                        <th className="pb-3">Model</th>
                        <th className="pb-3">Duration</th>
                        <th className="pb-3">Tokens</th>
                        <th className="pb-3">Tools</th>
                        <th className="pb-3">Judge Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                      {analytics.recent_agent_metrics.map((m) => (
                        <tr key={m.id} className="hover:bg-zinc-800/30">
                          <td className="py-3 font-semibold capitalize text-white">{m.agent_name}</td>
                          <td className="py-3 font-mono text-indigo-300">{m.model}</td>
                          <td className="py-3">{m.duration}s</td>
                          <td className="py-3 font-mono">{m.total_tokens}</td>
                          <td className="py-3">{m.tool_calls}</td>
                          <td className="py-3 font-bold text-emerald-400">{m.score} / 10</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Model Comparison Tab */}
          {activeTab === "models" && analytics && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                LLM Model Benchmarking & Speed Comparison
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {analytics.model_stats.map((m) => (
                  <div key={m.model_name} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm space-y-4">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                      <span className="text-base font-bold text-white font-mono">{m.model_name}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {m.total_calls} Calls
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800">
                        <div className="text-[10px] text-zinc-500 uppercase">Avg Speed</div>
                        <div className="text-lg font-bold text-white mt-1">{m.avg_duration}s</div>
                      </div>
                      <div className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800">
                        <div className="text-[10px] text-zinc-500 uppercase">Avg Tokens</div>
                        <div className="text-lg font-bold text-white mt-1">{m.avg_tokens}</div>
                      </div>
                      <div className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800">
                        <div className="text-[10px] text-zinc-500 uppercase">Quality Score</div>
                        <div className="text-lg font-bold text-emerald-400 mt-1">{m.avg_score} / 10</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tools & RAG Tab */}
          {activeTab === "tools_rag" && analytics && (
            <div className="space-y-6">
              {/* RAG Analytics */}
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <Database className="h-4 w-4 text-indigo-400" /> RAG Search & Vectorstore Analytics
                </h3>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                  <div className="bg-zinc-950/60 p-4 rounded-lg border border-zinc-800">
                    <div className="text-xs text-zinc-500 uppercase">Total Queries</div>
                    <div className="text-xl font-bold text-white mt-1">{analytics.rag_stats.total_queries}</div>
                  </div>
                  <div className="bg-zinc-950/60 p-4 rounded-lg border border-zinc-800">
                    <div className="text-xs text-zinc-500 uppercase">Avg Retrieval Latency</div>
                    <div className="text-xl font-bold text-indigo-300 mt-1">{analytics.rag_stats.avg_retrieval_latency}s</div>
                  </div>
                  <div className="bg-zinc-950/60 p-4 rounded-lg border border-zinc-800">
                    <div className="text-xs text-zinc-500 uppercase">Avg Similarity Score</div>
                    <div className="text-xl font-bold text-emerald-400 mt-1">{analytics.rag_stats.avg_similarity_score}</div>
                  </div>
                  <div className="bg-zinc-950/60 p-4 rounded-lg border border-zinc-800">
                    <div className="text-xs text-zinc-500 uppercase">Chunks Retrieved</div>
                    <div className="text-xl font-bold text-white mt-1">{analytics.rag_stats.total_chunks_retrieved}</div>
                  </div>
                </div>
              </div>

              {/* MCP Tools Stats */}
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <Wrench className="h-4 w-4 text-orange-400" /> MCP Tool Invocation Metrics
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {analytics.tool_stats.map((t) => (
                    <div key={t.tool_name} className="p-4 rounded-lg bg-zinc-950/60 border border-zinc-800 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-semibold text-orange-300">{t.tool_name}</span>
                        <span className="text-[10px] text-emerald-400 font-bold">{t.success_rate}% Success</span>
                      </div>
                      <div className="text-xs text-zinc-400">
                        Calls: <span className="text-white font-bold">{t.total_calls}</span> | Avg Duration: <span className="text-white font-bold">{t.avg_duration}s</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Prompt Registry Tab */}
          {activeTab === "prompts" && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                  Prompt Version Registry ({prompts.length})
                </h2>
                <Button
                  onClick={() => setShowPromptModal(true)}
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
                >
                  <Plus className="h-4 w-4 mr-1.5" /> New Prompt Version
                </Button>
              </div>

              <div className="space-y-4">
                {prompts.map((p) => (
                  <div key={p.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-bold text-white capitalize">{p.agent_name} Agent</span>
                        <span className="px-2 py-0.5 rounded text-xs font-mono bg-zinc-800 text-indigo-300">{p.version}</span>
                        {p.active && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Active
                          </span>
                        )}
                      </div>

                      {!p.active && (
                        <Button
                          onClick={() => handleActivatePrompt(p.id)}
                          disabled={actionLoading}
                          variant="outline"
                          size="sm"
                          className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                        >
                          <Check className="h-3.5 w-3.5 mr-1" /> Activate
                        </Button>
                      )}
                    </div>

                    <p className="text-xs text-zinc-400">{p.description || "System prompt template"}</p>

                    <div className="bg-zinc-950/80 p-3 rounded-lg border border-zinc-800 font-mono text-[11px] text-zinc-300 max-h-36 overflow-y-auto leading-relaxed">
                      {p.template}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* New Prompt Version Modal */}
      {showPromptModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Code2 className="h-5 w-5 text-emerald-400" /> Create Prompt Version
            </h3>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-zinc-400 mb-1 block">Agent</label>
                  <select
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white"
                  >
                    <option value="planner">Planner</option>
                    <option value="research">Research</option>
                    <option value="coder">Coder</option>
                    <option value="tester">Tester</option>
                    <option value="reviewer">Reviewer</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-zinc-400 mb-1 block">Version Tag</label>
                  <input
                    type="text"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="v2.0"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-400 mb-1 block">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Improved SOLID compliance guidelines"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-400 mb-1 block">System Prompt Template</label>
                <textarea
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  placeholder="Enter full system prompt template..."
                  rows={6}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white font-mono"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button
                onClick={() => setShowPromptModal(false)}
                variant="outline"
                size="sm"
                className="border-zinc-800 text-zinc-400"
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreatePrompt}
                disabled={actionLoading}
                size="sm"
                className="bg-emerald-600 text-white"
              >
                Save & Activate
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
