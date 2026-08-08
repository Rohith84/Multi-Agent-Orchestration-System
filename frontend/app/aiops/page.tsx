/**
 * Enterprise AI Operations (AIOps) Studio Dashboard.
 *
 * Features:
 * - Centralized Model Registry
 * - Intelligent Model Router & Automatic Fallback Engine
 * - LLM Agent Evaluator (Accuracy, Grounding, Hallucination, Code Quality, Safety)
 * - Automated Benchmark Suite Center
 * - User Feedback Engine & Unified Quality Scores
 * - Drift Detection (Model, Prompt, KB, Workflow, Embedding)
 * - Self-Optimization Engine (Non-mutating recommendations)
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Cpu,
  Route,
  Target,
  BarChart3,
  TrendingDown,
  Sparkles,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Zap,
  ThumbsUp,
  ThumbsDown,
  ShieldCheck,
  Award,
  Layers,
  Activity,
  Sliders,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchModels,
  fetchRoutingLogs,
  decideModelRoute,
  fetchEvaluations,
  fetchBenchmarks,
  runBenchmark,
  fetchDriftReports,
  fetchOptimizationRecommendations,
  submitFeedback,
  type ModelRegistryItem,
  type ModelRoutingLog,
  type RouteDecisionResponse,
  type EvaluationReport,
  type BenchmarkRun,
  type DriftReport,
  type OptimizationRecommendation,
} from "@/services/aiops-service";

type AIOpsTab = "registry" | "router" | "evals" | "benchmarks" | "drift" | "optimizations";

export default function AIOpsPage() {
  const [activeTab, setActiveTab] = useState<AIOpsTab>("registry");
  const [models, setModels] = useState<ModelRegistryItem[]>([]);
  const [routingLogs, setRoutingLogs] = useState<ModelRoutingLog[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationReport[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkRun[]>([]);
  const [driftReports, setDriftReports] = useState<DriftReport[]>([]);
  const [recommendations, setRecommendations] = useState<OptimizationRecommendation[]>([]);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // Router Simulator State
  const [simTaskType, setSimTaskType] = useState("code_synthesis");
  const [simRole, setSimRole] = useState("Coder");
  const [simComplexity, setSimComplexity] = useState("HIGH");
  const [simRouteResult, setSimRouteResult] = useState<RouteDecisionResponse | null>(null);

  // Feedback State
  const [feedbackSent, setFeedbackSent] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [mList, rLogs, eList, bList, dList, oList] = await Promise.all([
        fetchModels(),
        fetchRoutingLogs(),
        fetchEvaluations(),
        fetchBenchmarks(),
        fetchDriftReports(),
        fetchOptimizationRecommendations(),
      ]);
      setModels(mList);
      setRoutingLogs(rLogs);
      setEvaluations(eList);
      setBenchmarks(bList);
      setDriftReports(dList);
      setRecommendations(oList);
    } catch (err) {
      console.error("Failed to load AIOps data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSimulateRoute = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await decideModelRoute({
        task_type: simTaskType,
        agent_role: simRole,
        reasoning_complexity: simComplexity,
        vision_required: simTaskType === "vision_analysis",
      });
      setSimRouteResult(res);
      await loadData();
    } catch (err) {
      console.error("Route simulation failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunBenchmarkSuite = async () => {
    setActionLoading(true);
    try {
      await runBenchmark({
        suite_name: "full_aiops_benchmark",
        target_model: models[0]?.model_name || "qwen2.5-coder:7b",
      });
      await loadData();
    } catch (err) {
      console.error("Benchmark run failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSendFeedback = async (score: number) => {
    try {
      await submitFeedback({
        workflow_run_id: "wf_aiops_live_01",
        rating_type: "THUMBS",
        rating_score: score,
        feedback_text: score > 0 ? "Outstanding execution speed and code accuracy!" : "Needs higher grounding.",
      });
      setFeedbackSent(true);
      setTimeout(() => setFeedbackSent(false), 3000);
      await loadData();
    } catch (err) {
      console.error("Feedback failed:", err);
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
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Cpu className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Self-Optimizing AIOps Platform</h1>
              <p className="text-sm text-zinc-400">
                Model Registry • Intelligent Router • LLM Evaluation • Benchmarking • Drift & Optimization
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
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh Telemetry
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2 mb-6 border-b border-zinc-800 pb-3 overflow-x-auto">
        {[
          { id: "registry", label: "Model Registry", icon: Cpu },
          { id: "router", label: "Intelligent Router", icon: Route },
          { id: "evals", label: "LLM Evaluation & Quality", icon: Target },
          { id: "benchmarks", label: "Automated Benchmarks", icon: BarChart3 },
          { id: "drift", label: "Drift Detection", icon: TrendingDown },
          { id: "optimizations", label: "Self-Optimization", icon: Sparkles },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as AIOpsTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                isActive
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
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
          <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* TAB 1: MODEL REGISTRY */}
          {activeTab === "registry" && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                Centralized Model Registry ({models.length} Registered Models)
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
                {models.map((m) => (
                  <div key={m.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-4">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-bold text-white">{m.model_name}</h3>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                            m.health_status === "HEALTHY" ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" : "bg-amber-500/20 text-amber-300 border-amber-500/30"
                          }`}>
                            {m.health_status}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 font-mono mt-0.5">
                          Provider: {m.provider} • Version: {m.version} • {m.is_local ? "Local LLM" : "Cloud API"}
                        </p>
                      </div>

                      <div className="text-right">
                        <div className="text-sm font-bold text-emerald-400 font-mono">{m.avg_quality_score}%</div>
                        <div className="text-[10px] text-zinc-500">Quality Score</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center text-xs bg-zinc-950 p-3 rounded-lg border border-zinc-800 font-mono">
                      <div>
                        <div className="text-zinc-400 text-[10px]">Avg Latency</div>
                        <div className="text-white font-bold">{m.avg_latency_ms} ms</div>
                      </div>
                      <div>
                        <div className="text-zinc-400 text-[10px]">Context Window</div>
                        <div className="text-white font-bold">{(m.context_window / 1024).toFixed(0)}k</div>
                      </div>
                      <div>
                        <div className="text-zinc-400 text-[10px]">Availability</div>
                        <div className="text-white font-bold">{m.availability}%</div>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <div className="text-[11px] font-semibold text-zinc-400">Capabilities:</div>
                      <div className="flex flex-wrap gap-1">
                        {m.capabilities.map((cap, idx) => (
                          <span key={idx} className="text-[10px] font-mono bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800 text-zinc-300">
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: INTELLIGENT ROUTER */}
          {activeTab === "router" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Routing Simulator */}
              <div className="space-y-4">
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Route className="h-4 w-4 text-indigo-400" /> Route Simulator
                  </h3>

                  <form onSubmit={handleSimulateRoute} className="space-y-3">
                    <div>
                      <label className="text-[11px] font-semibold text-zinc-300 block mb-1">Task Type</label>
                      <select
                        value={simTaskType}
                        onChange={(e) => setSimTaskType(e.target.value)}
                        className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="code_synthesis">Code Synthesis</option>
                        <option value="planning">Architecture Planning</option>
                        <option value="web_research">Web Research</option>
                        <option value="vision_analysis">Vision Analysis</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-zinc-300 block mb-1">Agent Role</label>
                      <select
                        value={simRole}
                        onChange={(e) => setSimRole(e.target.value)}
                        className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="Coder">Coder</option>
                        <option value="Planner">Planner</option>
                        <option value="Research">Research</option>
                        <option value="Reviewer">Reviewer</option>
                        <option value="Vision">Vision</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-zinc-300 block mb-1">Reasoning Complexity</label>
                      <select
                        value={simComplexity}
                        onChange={(e) => setSimComplexity(e.target.value)}
                        className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="LOW">LOW</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="HIGH">HIGH</option>
                      </select>
                    </div>

                    <Button
                      type="submit"
                      disabled={actionLoading}
                      size="sm"
                      className="w-full bg-indigo-500 hover:bg-indigo-600 text-white font-bold text-xs"
                    >
                      {actionLoading ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Decide Optimal Route"}
                    </Button>
                  </form>
                </div>

                {/* Routing Simulation Result */}
                {simRouteResult && (
                  <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 space-y-2 backdrop-blur-sm">
                    <div className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                      <CheckCircle2 className="h-4 w-4" /> Routing Decision Result:
                    </div>
                    <div className="text-xs text-white font-mono bg-zinc-950 p-2.5 rounded border border-zinc-800 space-y-1">
                      <div>Primary Model: <span className="text-emerald-400 font-bold">{simRouteResult.selected_model}</span></div>
                      <div>Fallback Model: <span className="text-amber-400 font-bold">{simRouteResult.fallback_model}</span></div>
                      <div className="text-[10px] text-zinc-400 mt-1">{simRouteResult.routing_reason}</div>
                    </div>
                  </div>
                )}
              </div>

              {/* Logs */}
              <div className="lg:col-span-2 space-y-4">
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                  Routing Logs & Fallback History ({routingLogs.length})
                </h2>

                <div className="space-y-3">
                  {routingLogs.map((log) => (
                    <div key={log.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 backdrop-blur-sm space-y-2">
                      <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-indigo-300 bg-indigo-500/20 px-2 py-0.5 rounded border border-indigo-500/30">
                            {log.task_type}
                          </span>
                          <span className="text-xs text-zinc-400">Role: {log.agent_role}</span>
                        </div>
                        <span className="text-[10px] font-mono text-zinc-500">{new Date(log.created_at).toLocaleTimeString()}</span>
                      </div>

                      <div className="flex items-center justify-between text-xs font-mono">
                        <div>
                          Routed to: <span className="text-emerald-400 font-bold">{log.selected_model}</span>
                        </div>
                        <div className="text-zinc-500">
                          Fallback: <span className="text-amber-400">{log.fallback_model || "None"}</span>
                        </div>
                      </div>

                      <p className="text-[11px] text-zinc-400">{log.routing_reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: LLM EVALUATION & QUALITY */}
          {activeTab === "evals" && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                  Structured LLM Evaluations & Quality Reports
                </h2>

                <div className="flex gap-2">
                  <Button onClick={() => handleSendFeedback(5)} size="sm" variant="outline" className="text-xs border-emerald-500/30 text-emerald-300">
                    <ThumbsUp className="h-3.5 w-3.5 mr-1" /> Thumbs Up
                  </Button>
                  <Button onClick={() => handleSendFeedback(0)} size="sm" variant="outline" className="text-xs border-rose-500/30 text-rose-300">
                    <ThumbsDown className="h-3.5 w-3.5 mr-1" /> Thumbs Down
                  </Button>
                </div>
              </div>

              {feedbackSent && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs rounded-lg flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" /> User feedback recorded! Quality scores updated.
                </div>
              )}

              <div className="space-y-4">
                {evaluations.map((ev) => (
                  <div key={ev.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                      <div className="flex items-center gap-3">
                        <Award className="h-5 w-5 text-indigo-400" />
                        <div>
                          <h3 className="text-sm font-bold text-white">Agent: {ev.agent_role}</h3>
                          <span className="text-[10px] text-zinc-500 font-mono">Workflow: {ev.workflow_run_id}</span>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="text-base font-bold text-emerald-400 font-mono">{ev.overall_score}%</div>
                        <div className="text-[10px] text-zinc-500">Overall Score</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs bg-zinc-950 p-3 rounded-lg border border-zinc-800 font-mono">
                      <div>
                        <div className="text-zinc-500 text-[10px]">Accuracy</div>
                        <div className="text-white font-bold">{ev.accuracy}%</div>
                      </div>
                      <div>
                        <div className="text-zinc-500 text-[10px]">Grounding</div>
                        <div className="text-white font-bold">{ev.grounding}%</div>
                      </div>
                      <div>
                        <div className="text-zinc-500 text-[10px]">Code Quality</div>
                        <div className="text-white font-bold">{ev.code_quality}%</div>
                      </div>
                      <div>
                        <div className="text-zinc-500 text-[10px]">Safety</div>
                        <div className="text-white font-bold">{ev.safety}%</div>
                      </div>
                    </div>

                    <p className="text-xs text-zinc-300 italic">"{ev.summary}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: AUTOMATED BENCHMARKS */}
          {activeTab === "benchmarks" && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                  Automated Benchmark Runs ({benchmarks.length})
                </h2>

                <Button
                  onClick={handleRunBenchmarkSuite}
                  disabled={actionLoading}
                  size="sm"
                  className="bg-indigo-500 hover:bg-indigo-600 text-white font-bold text-xs"
                >
                  <BarChart3 className="h-4 w-4 mr-2" /> Run Benchmark Suite
                </Button>
              </div>

              <div className="space-y-3">
                {benchmarks.map((b) => (
                  <div key={b.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 backdrop-blur-sm space-y-2">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-white">{b.suite_name}</span>
                        <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                          {b.target_model}
                        </span>
                      </div>
                      <span className="text-xs font-bold text-emerald-400 font-mono">{b.overall_benchmark_score}% Benchmark Score</span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-zinc-400 font-mono">
                      <span>Accuracy: {b.accuracy_score}%</span>
                      <span>Latency: {b.latency_score}%</span>
                      <span>Cost Efficiency: {b.cost_score}%</span>
                      <span>Duration: {b.duration_ms} ms</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: DRIFT DETECTION */}
          {activeTab === "drift" && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                Drift Detection Alerts ({driftReports.length} Reports)
              </h2>

              <div className="space-y-3">
                {driftReports.map((d) => (
                  <div key={d.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 backdrop-blur-sm flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <TrendingDown className="h-5 w-5 text-amber-400" />
                      <div>
                        <div className="text-xs font-bold text-white">{d.drift_type} DRIFT: {d.target_identifier}</div>
                        <div className="text-[10px] text-zinc-400 font-mono">Baseline: {d.baseline_score}% → Current: {d.current_score}%</div>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className={`text-xs font-bold font-mono ${d.drift_delta < -5 ? "text-rose-400" : "text-amber-400"}`}>
                        Delta: {d.drift_delta}%
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {d.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: SELF-OPTIMIZATION */}
          {activeTab === "optimizations" && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                Non-Mutating Self-Optimization Recommendations ({recommendations.length})
              </h2>

              <div className="space-y-3">
                {recommendations.map((rec) => (
                  <div key={rec.id} className="rounded-xl border border-indigo-500/20 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 p-5 backdrop-blur-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-indigo-400" />
                        <span className="text-xs font-bold text-indigo-300 uppercase font-mono">{rec.category}</span>
                        <span className="text-xs text-zinc-400">Target: {rec.target_id}</span>
                      </div>

                      <span className="text-xs font-bold text-emerald-400 font-mono">
                        +{rec.score_impact_estimate}% Impact
                      </span>
                    </div>

                    <p className="text-xs font-bold text-white">{rec.recommended_action}</p>
                    <p className="text-[11px] text-zinc-400 font-mono">Reasoning: {rec.reasoning_summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}
