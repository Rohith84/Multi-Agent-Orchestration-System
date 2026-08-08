/**
 * /app — Application Command Center Dashboard.
 *
 * Inner dashboard page inside the /app/* application shell.
 * Connects to live system status API and provides quick access
 * to agents, chat assistant, workflows, and tools.
 */

"use client";

import Link from "next/link";
import { useSystemStatus } from "@/hooks/use-system-status";
import {
  MessageSquare,
  Bot,
  Layers,
  Wrench,
  BarChart3,
  RefreshCw,
  AlertTriangle,
  ArrowRight,
  Zap,
  Brain,
  Search,
  Code,
  TestTube,
  CheckCircle,
  Activity,
} from "lucide-react";

const FIVE_AGENTS = [
  { name: "Planner", icon: Brain, color: "var(--agent-planner)", task: "Breaks goals into structured execution plans" },
  { name: "Researcher", icon: Search, color: "var(--agent-researcher)", task: "Searches web and retrieves vector knowledge context" },
  { name: "Coder", icon: CoderIcon, color: "var(--agent-coder)", task: "Generates clean, typed, executable code" },
  { name: "Tester", icon: TestTube, color: "var(--agent-tester)", task: "Runs test suites and validates output correctness" },
  { name: "Reviewer", icon: CheckCircle, color: "var(--agent-reviewer)", task: "Audits security, quality, and compliance" },
];

function CoderIcon(props: any) {
  return <Code {...props} />;
}

export default function AppDashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } = useSystemStatus();

  const getStatus = (status?: string) => {
    if (isLoading) return "loading";
    if (isError || !status) return "offline";
    return status === "connected" ? "online" : "offline";
  };

  const backendStatus = getStatus(data?.backend?.status);
  const dbStatus = getStatus(data?.database?.status);
  const ollamaStatus = isLoading ? "loading" : isError ? "offline" : getStatus(data?.ollama?.status);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">

      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-6 brutalist-card"
           style={{ background: "var(--bg-surface)" }}>
        <div>
          <div className="inline-block mb-2">
            <span className="brutalist-btn-primary text-caption px-2.5 py-0.5 border"
                  style={{ borderColor: "var(--border-primary)" }}>
              COMMAND CENTER
            </span>
          </div>
          <h1 className="text-h1 font-black tracking-tight" style={{ color: "var(--fg-primary)" }}>
            MultiAgent OS Overview
          </h1>
          <p className="text-body-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
            Real-time status of multi-agent execution pipeline, system probes, and platform services.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="brutalist-btn brutalist-btn-secondary text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <Link href="/app/chat" className="brutalist-btn brutalist-btn-primary text-xs">
            <Zap className="w-3.5 h-3.5" />
            Launch Assistant
          </Link>
        </div>
      </div>

      {/* Error Alert */}
      {isError && (
        <div className="p-4 border-2 flex items-center gap-3"
             style={{ borderColor: "var(--accent-error)", background: "rgba(239,68,68,0.05)" }}>
          <AlertTriangle className="w-5 h-5 shrink-0" style={{ color: "var(--accent-error)" }} />
          <div className="flex-1">
            <p className="text-body-sm font-bold" style={{ color: "var(--accent-error)" }}>
              Backend Connection Unreachable
            </p>
            <p className="text-caption mt-0.5" style={{ color: "var(--fg-secondary)" }}>
              {error?.message || "Could not reach FastAPI server."} Make sure backend is running on port 8000.
            </p>
          </div>
        </div>
      )}

      {/* System Pulse Grid */}
      <div>
        <h2 className="text-h4 mb-3" style={{ color: "var(--fg-primary)" }}>System Infrastructure</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatusBlock label="API BACKEND" value={backendStatus === "online" ? "ONLINE" : backendStatus === "loading" ? "CHECKING" : "OFFLINE"} status={backendStatus} />
          <StatusBlock label="POSTGRES DB" value={dbStatus === "online" ? "ONLINE" : dbStatus === "loading" ? "CHECKING" : "OFFLINE"} status={dbStatus} />
          <StatusBlock label="OLLAMA LLM" value={ollamaStatus === "online" ? "ONLINE" : ollamaStatus === "loading" ? "CHECKING" : "OFFLINE"} status={ollamaStatus} />
          <StatusBlock label="EXECUTION AGENTS" value="5 / 5 READY" status="online" />
        </div>
      </div>

      {/* 5 Specialized Agents Quick-Control */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-h2 font-extrabold" style={{ color: "var(--fg-primary)" }}>
              5 AI Execution Agents
            </h2>
            <p className="text-body-sm" style={{ color: "var(--fg-secondary)" }}>
              Coordinated by the Supervisor Orchestration Core.
            </p>
          </div>
          <Link href="/app/agents" className="text-xs font-bold uppercase underline underline-offset-4 flex items-center gap-1 hover:text-[var(--accent-secondary)] transition-colors">
            View Control Center <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {FIVE_AGENTS.map((agent) => (
            <div key={agent.name} className="brutalist-card-sm p-4 flex flex-col justify-between"
                 style={{ background: "var(--bg-surface)" }}>
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 border-2 border-[var(--border-primary)] flex items-center justify-center shrink-0"
                       style={{ background: agent.color }}>
                    <agent.icon className="w-3.5 h-3.5" style={{ color: "var(--fg-on-accent)" }} />
                  </div>
                  <span className="text-xs font-bold uppercase" style={{ color: "var(--fg-primary)" }}>{agent.name}</span>
                </div>
                <p className="text-caption mb-3" style={{ color: "var(--fg-secondary)" }}>{agent.task}</p>
              </div>
              <div className="flex items-center justify-between border-t border-[var(--border-secondary)] pt-2 mt-2">
                <span className="text-[10px] font-bold text-[var(--accent-success)]">READY</span>
                <span className="text-[10px] font-mono text-[var(--fg-tertiary)]">01..05</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Launch Action Cards */}
      <div>
        <h2 className="text-h4 mb-3" style={{ color: "var(--fg-primary)" }}>Quick Modules</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Agent Control Center", desc: "Inspect 5 agents & orchestration core", href: "/app/agents", icon: Bot, accent: "var(--agent-planner)" },
            { label: "AI Assistant", desc: "Chat with multi-agent streaming workflow", href: "/app/chat", icon: MessageSquare, accent: "var(--agent-coder)" },
            { label: "Workflows", desc: "Manage executions and approvals", href: "/app/workflows", icon: Layers, accent: "var(--agent-researcher)" },
            { label: "MCP Tools", desc: "Browser MCP tool executions & logs", href: "/app/tools", icon: Wrench, accent: "var(--agent-tester)" },
          ].map((card) => (
            <Link key={card.href} href={card.href} className="group">
              <div className="brutalist-card p-5 h-full flex flex-col justify-between"
                   style={{ background: "var(--bg-surface)" }}>
                <div>
                  <div className="w-9 h-9 border-2 border-[var(--border-primary)] flex items-center justify-center mb-3"
                       style={{ background: card.accent }}>
                    <card.icon className="w-4 h-4" style={{ color: "var(--fg-on-accent)" }} />
                  </div>
                  <h3 className="text-sm font-extrabold uppercase mb-1" style={{ color: "var(--fg-primary)" }}>
                    {card.label}
                  </h3>
                  <p className="text-caption" style={{ color: "var(--fg-secondary)" }}>
                    {card.desc}
                  </p>
                </div>
                <div className="mt-4 flex items-center text-xs font-bold text-[var(--fg-primary)] group-hover:text-[var(--accent-secondary)] transition-colors">
                  Open Module <ArrowRight className="w-3.5 h-3.5 ml-1 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

    </div>
  );
}

function StatusBlock({ label, value, status }: { label: string; value: string; status: "online" | "offline" | "loading" }) {
  return (
    <div className="brutalist-card-sm p-3.5" style={{ background: "var(--bg-surface)" }}>
      <div className="flex items-center gap-2 mb-1">
        <div className={`status-dot ${status === "online" ? "status-dot-online" : status === "offline" ? "status-dot-offline" : "status-dot-warning"}`} />
        <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--fg-tertiary)" }}>{label}</span>
      </div>
      <span className="text-sm font-black tracking-tight"
            style={{ color: status === "online" ? "var(--accent-success)" : status === "offline" ? "var(--accent-error)" : "var(--fg-tertiary)" }}>
        {value}
      </span>
    </div>
  );
}
