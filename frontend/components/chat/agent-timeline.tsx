/**
 * AgentTimeline — visualization component displaying the multi-agent execution status and history.
 * Contains collapsible panels to inspect inputs/outputs for each agent in detail.
 * Shows MCP tool invocations under each agent step.
 */

"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Terminal,
  Wrench,
  ShieldAlert,
  BarChart3,
} from "lucide-react";
import type { UIExecutionState } from "@/hooks/use-chat";

interface AgentTimelineProps {
  executions: Record<string, UIExecutionState>;
  activeAgent: string | null;
}

const AGENTS_LIST = ["planner", "research", "coder", "tester", "reviewer"];

export function AgentTimeline({ executions, activeAgent }: AgentTimelineProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [runningSeconds, setRunningSeconds] = useState<number>(0);

  useEffect(() => {
    if (!activeAgent) {
      setRunningSeconds(0);
      return;
    }
    setRunningSeconds(0);
    const interval = setInterval(() => {
      setRunningSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [activeAgent]);

  const toggleExpand = (agent: string) => {
    setExpandedAgent((prev) => (prev === agent ? null : agent));
  };

  const getAgentLabel = (agent: string) => {
    switch (agent) {
      case "planner":
        return "🧠 Planner Agent";
      case "research":
        return "🔎 Research Agent";
      case "coder":
        return "💻 Coder Agent";
      case "tester":
        return "🧪 Tester Agent";
      case "reviewer":
        return "🔍 Reviewer Agent";
      default:
        return agent.toUpperCase();
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Loader2 className="h-5 w-5 text-violet-400 animate-spin" />;
      case "paused_approval":
        return <ShieldAlert className="h-5 w-5 text-amber-400 animate-pulse" />;
      case "retrying":
        return <Loader2 className="h-5 w-5 text-amber-400 animate-spin" />;
      case "success":
        return <CheckCircle2 className="h-5 w-5 text-emerald-400" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-400" />;
      default:
        return <div className="h-2 w-2 rounded-full bg-zinc-700" />;
    }
  };

  const getStatusClasses = (status: string) => {
    switch (status) {
      case "running":
        return "border-2 border-[var(--accent-secondary)] bg-[var(--bg-surface)] text-[var(--fg-primary)] shadow-sm";
      case "paused_approval":
        return "border-2 border-[var(--accent-warning)] bg-[var(--bg-surface)] text-[var(--fg-primary)] ring-2 ring-amber-500/30";
      case "retrying":
        return "border-2 border-[var(--accent-warning)] bg-[var(--bg-surface)] text-[var(--fg-primary)]";
      case "success":
        return "border-2 border-[var(--accent-success)] bg-[var(--bg-surface)] text-[var(--fg-primary)]";
      case "failed":
        return "border-2 border-[var(--accent-error)] bg-[var(--bg-surface)] text-[var(--fg-primary)]";
      default:
        return "border-2 border-[var(--border-primary)] bg-[var(--bg-secondary)] text-[var(--fg-primary)] shadow-[var(--shadow-brutalist-sm)]";
    }
  };

  return (
    <div
      className="w-80 h-full border-l flex flex-col transition-colors"
      style={{
        background: "var(--bg-surface)",
        borderColor: "var(--border-secondary)",
      }}
    >
      <div
        className="px-6 py-4 border-b flex items-center justify-between"
        style={{ borderColor: "var(--border-secondary)" }}
      >
        <h2
          className="text-sm font-black flex items-center gap-2 tracking-tight"
          style={{ color: "var(--fg-primary)" }}
        >
          <Terminal className="h-4 w-4 text-[var(--accent-secondary)]" />
          Agent Execution Timeline
        </h2>
        {activeAgent && (
          <span
            className="flex items-center gap-1.5 text-xs font-bold"
            style={{ color: "var(--accent-secondary)" }}
          >
            <span className="h-2 w-2 rounded-full bg-[var(--accent-secondary)] animate-pulse" />
            Active
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {AGENTS_LIST.map((agent, index) => {
          const state = executions[agent] || {
            agentName: agent,
            status: "idle",
            output: "",
            executionTime: 0,
            toolInvocations: [],
          };
          const isExpanded = expandedAgent === agent;
          const statusClasses = getStatusClasses(state.status);
          const toolInvocations = state.toolInvocations || [];

          return (
            <div
              key={agent}
              className={`rounded-lg transition-all duration-300 ${statusClasses}`}
            >
              {/* Header */}
              <div
                onClick={() => state.output && toggleExpand(agent)}
                className={`flex items-center justify-between p-3.5 ${
                  state.output ? "cursor-pointer hover:opacity-90" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 flex items-center justify-center h-7 w-7">
                    {getStatusIcon(state.status)}
                  </div>
                  <div>
                    <h3
                      className="text-xs font-black tracking-tight"
                      style={{ color: "var(--fg-primary)" }}
                    >
                      {getAgentLabel(agent)}
                    </h3>
                    {agent === "coder" && state.status === "success" && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-400/90 mt-0.5">
                        <span className="font-bold">✓</span> Code generated
                      </div>
                    )}
                    {agent === "coder" && state.status === "failed" && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-red-400 mt-0.5">
                        <span className="font-bold">✗</span> Code generation failed
                      </div>
                    )}
                    {agent === "tester" && state.status === "success" && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-400/90 mt-0.5">
                        <span className="font-bold">✓</span> Test generation & coverage analysis
                      </div>
                    )}
                    {agent === "reviewer" && state.status === "success" && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-400/90 mt-0.5">
                        <span className="font-bold">✓</span> Quality Gate Passed
                      </div>
                    )}
                    {agent === "reviewer" && state.status === "failed" && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-red-400 mt-0.5">
                        <span className="font-bold">✗</span> Quality Gate Rejected
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {(state.status === "running" || state.status === "retrying") && activeAgent === agent ? (
                    <div
                      className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-violet-950/40 border border-violet-800/40 text-violet-300 animate-pulse"
                    >
                      <Clock className="h-3 w-3 text-violet-400 animate-spin" />
                      {runningSeconds}s
                    </div>
                  ) : state.executionTime > 0 ? (
                    <div
                      className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700/50"
                    >
                      <Clock className="h-3 w-3 text-zinc-400" />
                      {state.executionTime}s
                    </div>
                  ) : null}

                  {state.output && (
                    <div>
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-zinc-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-zinc-500" />
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Tool Invocations */}
              {toolInvocations.length > 0 && (
                <div className="px-4 pb-2 space-y-1.5">
                  {toolInvocations.map((inv, idx) => (
                    <div
                      key={`${inv.toolName}-${idx}`}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800/40 border border-zinc-700/30"
                    >
                      <Wrench className="h-3 w-3 text-orange-400 flex-shrink-0" />
                      <span className="text-[10px] font-mono text-orange-300 flex-1 truncate">
                        {inv.toolName}
                      </span>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span className="text-[10px] text-zinc-500">
                          {inv.executionTime}s
                        </span>
                        {inv.status === "success" ? (
                          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                        ) : (
                          <XCircle className="h-3 w-3 text-red-400" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Collapsible Content */}
              {isExpanded && state.output && (
                <div className="px-4 pb-4 pt-0 border-t border-zinc-800/50 mt-2">
                  <div className="bg-zinc-950/80 rounded-lg p-3 mt-2 border border-zinc-800/80 max-h-60 overflow-y-auto">
                    <pre className="text-[10px] font-mono text-zinc-300 whitespace-pre-wrap leading-relaxed">
                      {state.output}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
