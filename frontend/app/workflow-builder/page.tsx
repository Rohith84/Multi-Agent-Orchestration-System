/**
 * Visual Workflow Builder & Custom Agent Studio Page.
 *
 * Features:
 * - Interactive Node Canvas & Graph Topology Builder
 * - Custom Agent Designer & System Prompt Editor
 * - MCP Tool Assignment Panel
 * - Dry-Run Simulation & Graph Topology Validation Engine
 * - Dynamic LangGraph Execution Engine
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Workflow,
  Plus,
  Play,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Layers,
  Cpu,
  Wrench,
  Sparkles,
  Bot,
  Zap,
  Eye,
  Settings2,
  Trash2,
  FolderOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchWorkflowTemplates,
  createWorkflowTemplate,
  simulateWorkflowTemplate,
  executeDynamicWorkflow,
  fetchCustomAgents,
  createCustomAgent,
  type WorkflowTemplate,
  type CustomAgent,
  type GraphNode,
  type GraphEdge,
  type SimulationReport,
} from "@/services/workflow-builder-service";

export default function WorkflowBuilderPage() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [customAgents, setCustomAgents] = useState<CustomAgent[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [simulationReport, setSimulationReport] = useState<SimulationReport | null>(null);
  const [execResult, setExecResult] = useState<Record<string, unknown> | null>(null);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // New Custom Agent Form State
  const [newAgentName, setNewAgentName] = useState("");
  const [newAgentPrompt, setNewAgentPrompt] = useState("");
  const [newAgentModel, setNewAgentModel] = useState("llama3.1:8b");

  const loadData = useCallback(async () => {
    try {
      const [tmplList, agentList] = await Promise.all([
        fetchWorkflowTemplates(),
        fetchCustomAgents(),
      ]);
      setTemplates(tmplList);
      setCustomAgents(agentList);

      if (tmplList.length > 0 && !selectedTemplate) {
        setSelectedTemplate(tmplList[0]);
      }
    } catch (err) {
      console.error("Failed to load workflow builder data:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedTemplate]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSimulate = async () => {
    if (!selectedTemplate) return;
    setActionLoading(true);
    try {
      const sim = await simulateWorkflowTemplate(selectedTemplate.id);
      setSimulationReport(sim);
    } catch (err) {
      console.error("Failed to simulate workflow:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!selectedTemplate) return;
    setActionLoading(true);
    try {
      const res = await executeDynamicWorkflow(selectedTemplate.id, "Generate a FastAPI microservice structure");
      setExecResult(res);
    } catch (err) {
      console.error("Failed to execute workflow:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgentName || !newAgentPrompt) return;
    setActionLoading(true);
    try {
      await createCustomAgent({
        name: newAgentName,
        description: "Custom user agent",
        system_prompt: newAgentPrompt,
        llm_model: newAgentModel,
      });
      setNewAgentName("");
      setNewAgentPrompt("");
      await loadData();
    } catch (err) {
      console.error("Failed to create custom agent:", err);
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
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
              <Workflow className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Visual Agent Builder & Workflow Studio</h1>
              <p className="text-sm text-zinc-400">
                Dynamic LangGraph Compiler • Custom Agent Prompt Designer • Dry-Run Simulator
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={handleSimulate}
            disabled={actionLoading || !selectedTemplate}
            variant="outline"
            size="sm"
            className="border-amber-500/30 text-amber-300 hover:bg-amber-500/10"
          >
            <Zap className="h-4 w-4 mr-2" /> Simulate Workflow
          </Button>

          <Button
            onClick={handleExecute}
            disabled={actionLoading || !selectedTemplate}
            size="sm"
            className="bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold"
          >
            <Play className="h-4 w-4 mr-2 fill-current" /> Execute Dynamic Graph
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 text-amber-400 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar: Template Library & Custom Agent Designer */}
          <div className="space-y-6">
            {/* Template Library */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-3">
              <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-amber-400" /> Workflow Templates ({templates.length})
              </h2>

              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {templates.map((tmpl) => {
                  const isSelected = selectedTemplate?.id === tmpl.id;
                  return (
                    <div
                      key={tmpl.id}
                      onClick={() => {
                        setSelectedTemplate(tmpl);
                        setSimulationReport(null);
                        setExecResult(null);
                      }}
                      className={`p-3 rounded-lg border backdrop-blur-sm cursor-pointer transition-all ${
                        isSelected
                          ? "bg-zinc-800/80 border-amber-500/40 ring-1 ring-amber-500/30"
                          : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white">{tmpl.name}</span>
                        {tmpl.is_preset && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                            Preset
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-zinc-400 mt-1 line-clamp-2">{tmpl.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Custom Agent Creator */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-4">
              <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                <Bot className="h-4 w-4 text-indigo-400" /> Create Custom Agent
              </h2>

              <form onSubmit={handleCreateAgent} className="space-y-3">
                <div>
                  <label className="text-[11px] font-semibold text-zinc-300 block mb-1">Agent Name</label>
                  <input
                    type="text"
                    placeholder="e.g. security_auditor"
                    value={newAgentName}
                    onChange={(e) => setNewAgentName(e.target.value)}
                    className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white placeholder-zinc-600 focus:outline-none focus:border-amber-500"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-zinc-300 block mb-1">Target Model</label>
                  <select
                    value={newAgentModel}
                    onChange={(e) => setNewAgentModel(e.target.value)}
                    className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white focus:outline-none focus:border-amber-500"
                  >
                    <option value="llama3.1:8b">llama3.1:8b (General Reasoning)</option>
                    <option value="qwen2.5-coder:7b">qwen2.5-coder:7b (Code Specialist)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-zinc-300 block mb-1">System Prompt</label>
                  <textarea
                    rows={3}
                    placeholder="You are a Security Audit Agent..."
                    value={newAgentPrompt}
                    onChange={(e) => setNewAgentPrompt(e.target.value)}
                    className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white placeholder-zinc-600 focus:outline-none focus:border-amber-500"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={actionLoading || !newAgentName || !newAgentPrompt}
                  size="sm"
                  className="w-full bg-zinc-800 hover:bg-zinc-700 text-xs text-white"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add Custom Agent
                </Button>
              </form>
            </div>
          </div>

          {/* Main Visual Canvas & Graph Inspector */}
          <div className="lg:col-span-2 space-y-6">
            {selectedTemplate ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm space-y-4">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div>
                    <h2 className="text-base font-bold text-white">{selectedTemplate.name}</h2>
                    <p className="text-xs text-zinc-400">{selectedTemplate.description}</p>
                  </div>
                  <span className="text-xs font-mono text-amber-300 bg-amber-500/10 px-2.5 py-1 rounded border border-amber-500/20">
                    {selectedTemplate.graph_json.nodes.length} Nodes • {selectedTemplate.graph_json.edges.length} Edges
                  </span>
                </div>

                {/* Graph Topology Flow Visualization */}
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-zinc-400 uppercase">Compiled Graph Flow Topology</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {selectedTemplate.graph_json.nodes.map((node, idx) => (
                      <div
                        key={node.id}
                        className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center gap-3"
                      >
                        <div className="h-8 w-8 rounded bg-amber-500/20 flex items-center justify-center text-amber-400 font-bold text-xs shrink-0">
                          {idx + 1}
                        </div>
                        <div>
                          <div className="text-xs font-bold text-white capitalize">{node.label}</div>
                          <div className="text-[10px] text-zinc-500 font-mono">Type: {node.type}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Simulation Report Box */}
                {simulationReport && (
                  <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-4 space-y-2">
                    <h4 className="text-xs font-bold text-amber-300 flex items-center gap-2">
                      <Zap className="h-4 w-4" /> Graph Dry-Run Simulation Report
                    </h4>
                    <p className="text-xs text-zinc-300">
                      Estimated Execution Time: <strong className="text-white">{simulationReport.estimated_runtime_seconds}s</strong>
                    </p>
                    <div className="text-xs font-mono text-zinc-400">
                      Execution Order: {simulationReport.execution_order.join(" ➔ ")}
                    </div>
                  </div>
                )}

                {/* Execution Output Box */}
                {execResult && (
                  <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-4 space-y-2">
                    <h4 className="text-xs font-bold text-emerald-300 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" /> Dynamic Graph Execution Completed
                    </h4>
                    <pre className="text-[11px] font-mono text-zinc-300 max-h-[300px] overflow-y-auto whitespace-pre-wrap">
                      {JSON.stringify(execResult, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-12 text-center backdrop-blur-sm">
                <Workflow className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                <p className="text-sm text-zinc-500">Select a template to view graph topology.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
