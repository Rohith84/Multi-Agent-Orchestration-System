/**
 * /app/tools — Canonical Tool Center route inside the /app/* application shell.
 *
 * Features:
 * - List all available MCP tools with descriptions and parameter schemas
 * - Execute tools manually with a JSON arguments form
 * - View execution history with search, status badges, and duration display
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  Search,
  Wrench,
  Database,
  Globe,
  Terminal,
  FileText,
  Wifi,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Loader2,
  Zap,
  History,
  Box,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchTools,
  executeTool,
  fetchToolHistory,
  type ToolDefinition,
  type ToolExecution,
  type ToolRunResponse,
} from "@/services/tools-service";

type TabType = "tools" | "history";

const CATEGORY_ICONS: Record<string, typeof Wrench> = {
  filesystem: FileText,
  database: Database,
  github: Globe,
  http: Wifi,
  terminal: Terminal,
};

export default function ToolCenterPage() {
  const [activeTab, setActiveTab] = useState<TabType>("tools");
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [history, setHistory] = useState<ToolExecution[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [argsInput, setArgsInput] = useState("{}");
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ToolRunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedResult, setExpandedResult] = useState(false);

  // Load tools
  const loadTools = useCallback(async () => {
    try {
      const res = await fetchTools();
      setTools(res.tools);
    } catch (err) {
      console.error("Failed to load tools:", err);
    }
  }, []);

  // Load history
  const loadHistory = useCallback(async () => {
    try {
      const res = await fetchToolHistory({
        limit: 50,
        search: searchQuery || undefined,
      });
      setHistory(res.executions);
      setHistoryTotal(res.total);
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  }, [searchQuery]);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadTools(), loadHistory()]).finally(() => setLoading(false));
  }, [loadTools, loadHistory]);

  // Execute tool
  const handleExecute = async () => {
    if (!selectedTool) return;
    setExecuting(true);
    setExecutionResult(null);

    try {
      let parsedArgs = {};
      try {
        parsedArgs = JSON.parse(argsInput);
      } catch {
        setExecutionResult({
          success: false,
          tool_name: selectedTool.name,
          result: null,
          error: "Invalid JSON in arguments field.",
          execution_time: 0,
        });
        setExecuting(false);
        return;
      }

      const res = await executeTool({
        tool_name: selectedTool.name,
        arguments: parsedArgs,
        agent_name: "manual",
      });
      setExecutionResult(res);
      await loadHistory();
    } catch (err: any) {
      setExecutionResult({
        success: false,
        tool_name: selectedTool.name,
        result: null,
        error: err?.response?.data?.detail || err.message || "Execution failed",
        execution_time: 0,
      });
    } finally {
      setExecuting(false);
    }
  };

  // Select a tool and prepare default args
  const selectTool = (tool: ToolDefinition) => {
    setSelectedTool(tool);
    setExecutionResult(null);
    setExpandedResult(false);
    const defaultArgs: Record<string, string> = {};
    const props = tool.parameters?.properties || {};
    for (const [key] of Object.entries(props)) {
      if (tool.parameters?.required?.includes(key)) {
        defaultArgs[key] = "";
      }
    }
    setArgsInput(JSON.stringify(defaultArgs, null, 2));
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Card */}
      <div className="p-6 brutalist-card flex flex-col sm:flex-row sm:items-center justify-between gap-4" style={{ background: "var(--bg-surface)" }}>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Wrench className="w-5 h-5 text-[var(--accent-primary)]" />
            <h1 className="text-h1 font-black tracking-tight uppercase" style={{ color: "var(--fg-primary)" }}>
              MCP Tool Center
            </h1>
          </div>
          <p className="text-body-sm text-[var(--fg-secondary)]">
            Model Context Protocol tools registry • Manual execution &amp; historical audit logs
          </p>
        </div>

        <Link href="/app">
          <Button size="sm" className="brutalist-btn brutalist-btn-secondary text-xs">
            <ArrowLeft className="w-3.5 h-3.5 mr-1" />
            Command Center
          </Button>
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setActiveTab("tools")}
          className={`brutalist-btn text-xs ${
            activeTab === "tools"
              ? "brutalist-btn-primary"
              : "brutalist-btn-secondary"
          }`}
        >
          <Box className="w-3.5 h-3.5 mr-1 inline-block" />
          Available Tools ({tools.length})
        </button>
        <button
          onClick={() => {
            setActiveTab("history");
            loadHistory();
          }}
          className={`brutalist-btn text-xs ${
            activeTab === "history"
              ? "brutalist-btn-primary"
              : "brutalist-btn-secondary"
          }`}
        >
          <History className="w-3.5 h-3.5 mr-1 inline-block" />
          Execution Audit History ({historyTotal})
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-caption text-[var(--fg-tertiary)] py-16 text-center">
          Loading MCP tools registry...
        </div>
      )}

      {/* Tools Tab */}
      {!loading && activeTab === "tools" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tool List */}
          <div className="lg:col-span-2 space-y-3">
            {tools.map((tool) => {
              const Icon = CATEGORY_ICONS[tool.category] || Wrench;
              const isSelected = selectedTool?.name === tool.name;

              return (
                <div
                  key={tool.name}
                  onClick={() => selectTool(tool)}
                  style={{
                    borderColor: isSelected ? "var(--accent-primary)" : "var(--border-secondary)",
                    background: "var(--bg-surface)",
                  }}
                  className={`
                    p-4 border-2 cursor-pointer transition-all hover:border-[var(--border-primary)] flex items-center justify-between gap-4
                    ${isSelected ? "ring-2 ring-[var(--accent-primary)]" : ""}
                  `}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 border border-[var(--border-primary)] flex items-center justify-center shrink-0" style={{ background: "var(--bg-secondary)" }}>
                      <Icon className="w-4 h-4 text-[var(--fg-primary)]" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-black uppercase text-[var(--fg-primary)] truncate">
                          {tool.name}
                        </span>
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 border border-[var(--border-secondary)] text-[var(--accent-secondary)]">
                          {tool.category}
                        </span>
                      </div>
                      <p className="text-caption text-[var(--fg-tertiary)] truncate mt-0.5">
                        {tool.description}
                      </p>
                    </div>
                  </div>
                  <Zap className={`w-4 h-4 shrink-0 ${isSelected ? "text-[var(--accent-primary)]" : "text-[var(--fg-tertiary)]"}`} />
                </div>
              );
            })}
          </div>

          {/* Execution Panel */}
          <div className="space-y-4">
            {selectedTool ? (
              <div className="p-5 brutalist-card space-y-4" style={{ background: "var(--bg-surface)" }}>
                <div className="border-b-2 border-[var(--border-primary)] pb-3">
                  <span className="text-[10px] font-bold uppercase text-[var(--fg-tertiary)] block">
                    TOOL RUNNER
                  </span>
                  <h3 className="text-sm font-black uppercase text-[var(--fg-primary)]">
                    {selectedTool.name}
                  </h3>
                  <p className="text-caption text-[var(--fg-secondary)] mt-1">
                    {selectedTool.description}
                  </p>
                </div>

                {/* JSON Arguments Form */}
                <div>
                  <label className="text-caption font-bold uppercase block mb-1" style={{ color: "var(--fg-secondary)" }}>
                    JSON Arguments
                  </label>
                  <textarea
                    rows={6}
                    value={argsInput}
                    onChange={(e) => setArgsInput(e.target.value)}
                    className="w-full p-2.5 border-2 border-[var(--border-secondary)] bg-[var(--bg-primary)] font-mono text-xs text-[var(--fg-primary)] focus:outline-none"
                  />
                </div>

                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="brutalist-btn brutalist-btn-primary w-full text-xs"
                >
                  {executing ? "Executing Tool..." : "Execute Tool →"}
                </button>

                {/* Result Display */}
                {executionResult && (
                  <div className="p-3 border-2 border-[var(--border-primary)] bg-[var(--bg-secondary)] space-y-2">
                    <div className="flex items-center justify-between text-xs font-bold">
                      <span className={executionResult.success ? "text-[var(--accent-success)]" : "text-[var(--accent-error)]"}>
                        {executionResult.success ? "✓ Execution Success" : "✕ Execution Error"}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--fg-tertiary)]">
                        {executionResult.execution_time.toFixed(2)}s
                      </span>
                    </div>

                    <pre className="text-[10px] font-mono p-2 border border-[var(--border-secondary)] bg-[var(--bg-primary)] overflow-x-auto max-h-48 text-[var(--fg-primary)]">
                      {executionResult.error || JSON.stringify(executionResult.result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 brutalist-card text-center text-caption text-[var(--fg-tertiary)]" style={{ background: "var(--bg-surface)" }}>
                Select an MCP tool from the list to inspect parameter schemas and execute manual requests.
              </div>
            )}
          </div>
        </div>
      )}

      {/* History Tab */}
      {!loading && activeTab === "history" && (
        <div className="p-5 brutalist-card space-y-4" style={{ background: "var(--bg-surface)" }}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b-2 border-[var(--border-primary)] pb-3">
            <h3 className="text-xs font-black uppercase text-[var(--fg-primary)] flex items-center gap-2">
              <History className="h-4 w-4 text-[var(--accent-secondary)]" />
              Tool Execution Audit Logs ({history.length})
            </h3>

            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--fg-tertiary)]" />
              <input
                type="text"
                placeholder="Search history..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 border-2 border-[var(--border-secondary)] bg-[var(--bg-primary)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
              />
            </div>
          </div>

          {history.length === 0 ? (
            <div className="p-8 border-2 border-dashed border-[var(--border-secondary)] text-center text-caption text-[var(--fg-tertiary)]">
              No execution history records found.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b-2 border-[var(--border-primary)] text-[10px] font-black uppercase text-[var(--fg-tertiary)]">
                    <th className="p-2">Status</th>
                    <th className="p-2">Tool Name</th>
                    <th className="p-2">Invoked By Agent</th>
                    <th className="p-2">Duration</th>
                    <th className="p-2">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-secondary)]">
                  {history.map((item) => (
                    <tr key={item.id} className="hover:bg-[var(--bg-secondary)] text-xs font-mono">
                      <td className="p-2 font-bold">
                        <span className={`px-1.5 py-0.5 text-[9px] uppercase border ${
                          item.status === "completed" || item.status === "success"
                            ? "text-[var(--accent-success)] border-[var(--accent-success)]"
                            : "text-[var(--accent-error)] border-[var(--accent-error)]"
                        }`}>
                          {item.status || "completed"}
                        </span>
                      </td>
                      <td className="p-2 font-bold text-[var(--fg-primary)]">
                        {item.tool_name}
                      </td>
                      <td className="p-2 uppercase text-[10px] text-[var(--accent-secondary)]">
                        {item.agent_name || "manual"}
                      </td>
                      <td className="p-2 text-[10px] text-[var(--fg-tertiary)]">
                        {item.execution_time ? `${item.execution_time.toFixed(2)}s` : "--"}
                      </td>
                      <td className="p-2 text-[10px] text-[var(--fg-tertiary)]">
                        {formatDate(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
