/**
 * Tool Center — MCP tools management page.
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
  Play,
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

const CATEGORY_COLORS: Record<string, string> = {
  filesystem: "from-blue-600 to-cyan-500",
  database: "from-emerald-600 to-green-500",
  github: "from-purple-600 to-violet-500",
  http: "from-orange-600 to-amber-500",
  terminal: "from-rose-600 to-pink-500",
};

const CATEGORY_BORDER: Record<string, string> = {
  filesystem: "border-blue-500/20 hover:border-blue-500/40",
  database: "border-emerald-500/20 hover:border-emerald-500/40",
  github: "border-purple-500/20 hover:border-purple-500/40",
  http: "border-orange-500/20 hover:border-orange-500/40",
  terminal: "border-rose-500/20 hover:border-rose-500/40",
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
      // Refresh history
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
    for (const [key, val] of Object.entries(props)) {
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
    <main className="flex-1 p-6 sm:p-8 lg:p-12 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-orange-600 to-amber-500 flex items-center justify-center shadow-lg shadow-orange-500/20">
            <Wrench className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Tool Center</h1>
            <p className="text-sm text-zinc-400">
              MCP Tools • Execute & Monitor • {tools.length} tools available
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab("tools")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "tools"
              ? "bg-orange-500/20 text-orange-300 border border-orange-500/30"
              : "bg-zinc-800/50 text-zinc-400 border border-zinc-700/50 hover:text-white hover:border-zinc-600"
          }`}
        >
          <Box className="h-4 w-4" />
          Available Tools
        </button>
        <button
          onClick={() => {
            setActiveTab("history");
            loadHistory();
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "history"
              ? "bg-orange-500/20 text-orange-300 border border-orange-500/30"
              : "bg-zinc-800/50 text-zinc-400 border border-zinc-700/50 hover:text-white hover:border-zinc-600"
          }`}
        >
          <History className="h-4 w-4" />
          Execution History
          {historyTotal > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-zinc-700 text-zinc-300">
              {historyTotal}
            </span>
          )}
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 text-orange-400 animate-spin" />
        </div>
      )}

      {/* Tools Tab */}
      {!loading && activeTab === "tools" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tool List */}
          <div className="lg:col-span-2 space-y-3">
            {tools.map((tool) => {
              const Icon = CATEGORY_ICONS[tool.category] || Wrench;
              const gradient = CATEGORY_COLORS[tool.category] || "from-zinc-600 to-zinc-500";
              const border = CATEGORY_BORDER[tool.category] || "border-zinc-700/50";
              const isSelected = selectedTool?.name === tool.name;

              return (
                <div
                  key={tool.name}
                  onClick={() => selectTool(tool)}
                  className={`group relative overflow-hidden rounded-xl border p-4 backdrop-blur-sm cursor-pointer transition-all duration-300 hover:scale-[1.01] ${border} ${
                    isSelected
                      ? "bg-zinc-800/80 ring-1 ring-orange-500/30"
                      : "bg-zinc-900/40 hover:bg-zinc-800/40"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`h-10 w-10 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center shadow-md flex-shrink-0`}
                    >
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-white truncate">
                          {tool.name}
                        </h3>
                        <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-zinc-700/80 text-zinc-400 uppercase tracking-wider">
                          {tool.category}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 mt-0.5 line-clamp-1">
                        {tool.description}
                      </p>
                    </div>
                    <Zap className="h-4 w-4 text-zinc-600 group-hover:text-orange-400 transition-colors flex-shrink-0" />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Execution Panel */}
          <div className="space-y-4">
            {selectedTool ? (
              <>
                {/* Selected Tool Info */}
                <div className="rounded-xl border border-zinc-700/50 bg-zinc-900/60 p-5 backdrop-blur-sm">
                  <h3 className="text-sm font-semibold text-white mb-1">
                    {selectedTool.name}
                  </h3>
                  <p className="text-xs text-zinc-400 mb-4">
                    {selectedTool.description}
                  </p>

                  {/* Parameters */}
                  {Object.keys(selectedTool.parameters?.properties || {}).length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                        Parameters
                      </h4>
                      <div className="space-y-1.5">
                        {Object.entries(selectedTool.parameters?.properties || {}).map(
                          ([key, val]) => (
                            <div
                              key={key}
                              className="flex items-start gap-2 text-xs"
                            >
                              <code className="text-orange-300 font-mono bg-zinc-800 px-1.5 py-0.5 rounded">
                                {key}
                              </code>
                              <span className="text-zinc-500">
                                {val.type}
                                {selectedTool.parameters?.required?.includes(key) && (
                                  <span className="text-red-400 ml-1">*</span>
                                )}
                              </span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                  {/* Arguments Input */}
                  <div className="mb-4">
                    <h4 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                      Arguments (JSON)
                    </h4>
                    <textarea
                      value={argsInput}
                      onChange={(e) => setArgsInput(e.target.value)}
                      rows={5}
                      className="w-full bg-zinc-950 border border-zinc-700/50 rounded-lg p-3 text-xs font-mono text-zinc-300 resize-none focus:outline-none focus:ring-1 focus:ring-orange-500/50 focus:border-orange-500/50"
                      spellCheck={false}
                    />
                  </div>

                  {/* Execute Button */}
                  <Button
                    onClick={handleExecute}
                    disabled={executing}
                    className="w-full bg-gradient-to-r from-orange-600 to-amber-500 hover:from-orange-500 hover:to-amber-400 text-white font-medium text-sm"
                  >
                    {executing ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Executing...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Execute Tool
                      </>
                    )}
                  </Button>
                </div>

                {/* Execution Result */}
                {executionResult && (
                  <div
                    className={`rounded-xl border p-4 backdrop-blur-sm ${
                      executionResult.success
                        ? "border-emerald-500/20 bg-emerald-500/5"
                        : "border-red-500/20 bg-red-500/5"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {executionResult.success ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-400" />
                        )}
                        <span
                          className={`text-xs font-semibold ${
                            executionResult.success
                              ? "text-emerald-300"
                              : "text-red-300"
                          }`}
                        >
                          {executionResult.success ? "Success" : "Failed"}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 text-[10px] text-zinc-500">
                        <Clock className="h-3 w-3" />
                        {executionResult.execution_time}s
                      </div>
                    </div>

                    <div
                      className="cursor-pointer"
                      onClick={() => setExpandedResult(!expandedResult)}
                    >
                      <div className="flex items-center gap-1 text-xs text-zinc-400 mb-1">
                        {expandedResult ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )}
                        {expandedResult ? "Collapse" : "Expand"} Result
                      </div>
                    </div>

                    {expandedResult && (
                      <div className="bg-zinc-950/80 rounded-lg p-3 mt-2 border border-zinc-800/80 max-h-72 overflow-y-auto">
                        <pre className="text-[10px] font-mono text-zinc-300 whitespace-pre-wrap leading-relaxed">
                          {executionResult.success
                            ? JSON.stringify(executionResult.result, null, 2)
                            : executionResult.error}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-xl border border-zinc-700/50 bg-zinc-900/40 p-8 text-center backdrop-blur-sm">
                <Wrench className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                <p className="text-sm text-zinc-500">
                  Select a tool to execute
                </p>
                <p className="text-xs text-zinc-600 mt-1">
                  Click any tool from the list
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* History Tab */}
      {!loading && activeTab === "history" && (
        <div className="space-y-4">
          {/* Search */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by tool name, agent, or result..."
                className="w-full bg-zinc-900/60 border border-zinc-700/50 rounded-lg pl-10 pr-4 py-2.5 text-sm text-zinc-300 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-orange-500/50 focus:border-orange-500/50"
              />
            </div>
            <Button
              onClick={loadHistory}
              variant="outline"
              size="sm"
              className="border-zinc-700/50 text-zinc-400 hover:text-white"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* History Table */}
          {history.length === 0 ? (
            <div className="rounded-xl border border-zinc-700/50 bg-zinc-900/40 p-12 text-center backdrop-blur-sm">
              <History className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
              <p className="text-sm text-zinc-500">No executions yet</p>
              <p className="text-xs text-zinc-600 mt-1">
                Execute a tool to see its history here
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-zinc-700/50 bg-zinc-900/40 backdrop-blur-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="px-4 py-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                        Tool
                      </th>
                      <th className="px-4 py-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                        Agent
                      </th>
                      <th className="px-4 py-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-4 py-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                        Duration
                      </th>
                      <th className="px-4 py-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                        Time
                      </th>
                      <th className="px-4 py-3 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                        Result
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    {history.map((exec) => {
                      const cat = exec.tool_name.split(".")[0] || "unknown";
                      const Icon = CATEGORY_ICONS[cat] || Wrench;

                      return (
                        <tr
                          key={exec.id}
                          className="hover:bg-zinc-800/30 transition-colors"
                        >
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <Icon className="h-3.5 w-3.5 text-zinc-500" />
                              <span className="text-xs font-medium text-zinc-300">
                                {exec.tool_name}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs text-zinc-400 capitalize">
                              {exec.agent_name}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {exec.status === "success" ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                <CheckCircle2 className="h-3 w-3" />
                                Success
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
                                <XCircle className="h-3 w-3" />
                                Failed
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1 text-xs text-zinc-400">
                              <Clock className="h-3 w-3" />
                              {exec.execution_time}s
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs text-zinc-500">
                              {formatDate(exec.created_at)}
                            </span>
                          </td>
                          <td className="px-4 py-3 max-w-xs">
                            <p className="text-[10px] text-zinc-500 truncate font-mono">
                              {exec.result_summary.substring(0, 80)}
                              {exec.result_summary.length > 80 ? "..." : ""}
                            </p>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination info */}
              <div className="px-4 py-3 border-t border-zinc-800 text-xs text-zinc-500">
                Showing {history.length} of {historyTotal} executions
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
