/**
 * AgentTimeline — visualization component displaying the multi-agent execution status and history.
 * Contains collapsible panels to inspect inputs/outputs for each agent in detail.
 * Shows MCP tool invocations under each agent step.
 */

"use client";

import { useState } from "react";
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
} from "lucide-react";
import type { UIExecutionState } from "@/hooks/use-chat";

interface AgentTimelineProps {
  executions: Record<string, UIExecutionState>;
  activeAgent: string | null;
}

const AGENTS_LIST = ["planner", "research", "coder", "tester", "reviewer"];

export function AgentTimeline({ executions, activeAgent }: AgentTimelineProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

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
        return "border-violet-500/30 bg-violet-500/5 text-violet-300";
      case "paused_approval":
        return "border-amber-500/40 bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/30";
      case "retrying":
        return "border-amber-500/30 bg-amber-500/5 text-amber-300";
      case "success":
        return "border-emerald-500/30 bg-emerald-500/5 text-emerald-300";
      case "failed":
        return "border-red-500/30 bg-red-500/5 text-red-300";
      default:
        return "border-zinc-800 bg-zinc-900/20 text-zinc-500";
    }
  };

  return (
    <div className="w-80 h-full border-l border-zinc-800 bg-zinc-900/40 backdrop-blur-md flex flex-col">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Terminal className="h-4 w-4 text-violet-400" />
          Agent Execution Timeline
        </h2>
        {activeAgent && (
          <span className="flex items-center gap-1.5 text-xs text-violet-400">
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse" />
            Active
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
              className={`rounded-xl border transition-all duration-300 ${statusClasses}`}
            >
              {/* Header */}
              <div
                onClick={() => state.output && toggleExpand(agent)}
                className={`flex items-center justify-between p-4 ${
                  state.output ? "cursor-pointer hover:bg-zinc-800/20" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 flex items-center justify-center h-8 w-8">
                    {getStatusIcon(state.status)}
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold">{getAgentLabel(agent)}</h3>
                    {state.executionTime > 0 && (
                      <div className="flex items-center gap-1 mt-1 text-[10px] text-zinc-500">
                        <Clock className="h-3 w-3" />
                        {state.executionTime}s
                      </div>
                    )}
                  </div>
                </div>

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
