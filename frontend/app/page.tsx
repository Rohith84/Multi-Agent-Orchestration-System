/**
 * MultiAgent OS — Command Center
 *
 * Premium landing page with:
 * - Hero section with 3D orchestration visualization
 * - System Pulse (live backend status)
 * - Agent Command Center (7 agents)
 * - Live Orchestration flow
 * - Performance metrics
 * - Live activity feed
 * - Command Center quick actions
 * - Final CTA
 *
 * Preserves all existing backend connections via useSystemStatus hook.
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { AppNavbar } from "@/components/app-navbar";
import { AppFooter } from "@/components/app-footer";
import { useSystemStatus } from "@/hooks/use-system-status";
import { type StatusType } from "@/components/status-card";
import {
  RefreshCw,
  AlertTriangle,
  MessageSquare,
  FileText,
  Wrench,
  Layers,
  BarChart3,
  Activity,
  Folder,
  Sparkles,
  Workflow,
  ShieldCheck,
  Cpu,
  ArrowRight,
  Zap,
  Eye,
  Database,
  Server,
  Bot,
  Brain,
  Search,
  Code,
  TestTube,
  CheckCircle,
  Clock,
} from "lucide-react";

// Lazy-load 3D to keep initial bundle small
const Orchestration3D = dynamic(
  () => import("@/components/orchestration-3d").then((m) => ({ default: m.Orchestration3D })),
  { ssr: false, loading: () => <div className="w-full h-full flex items-center justify-center"><div className="text-caption" style={{ color: "var(--fg-tertiary)" }}>Loading 3D...</div></div> }
);

/* ── Agent Definitions ── */
const AGENTS = [
  { name: "Planner", icon: Brain, color: "var(--agent-planner)", status: "ACTIVE", task: "Generating execution plan", workload: 45, lastAction: "2s ago" },
  { name: "Researcher", icon: Search, color: "var(--agent-researcher)", status: "ACTIVE", task: "Analyzing data sources", workload: 72, lastAction: "5s ago" },
  { name: "Coder", icon: Code, color: "var(--agent-coder)", status: "ACTIVE", task: "Building API endpoint", workload: 67, lastAction: "1s ago" },
  { name: "Tester", icon: TestTube, color: "var(--agent-tester)", status: "STANDBY", task: "Awaiting code output", workload: 12, lastAction: "30s ago" },
  { name: "Reviewer", icon: CheckCircle, color: "var(--agent-reviewer)", status: "STANDBY", task: "Awaiting test results", workload: 8, lastAction: "45s ago" },
];

/* ── Live Activity Feed ── */
const ACTIVITY_EVENTS = [
  { agent: "Planner", color: "var(--agent-planner)", message: "Created execution plan for workflow #1248", time: "2s ago" },
  { agent: "Researcher", color: "var(--agent-researcher)", message: "Found 14 relevant sources across knowledge base", time: "5s ago" },
  { agent: "Coder", color: "var(--agent-coder)", message: "Generated API implementation — 142 lines", time: "8s ago" },
  { agent: "Tester", color: "var(--agent-tester)", message: "Detected 2 edge cases in test suite", time: "15s ago" },
  { agent: "Reviewer", color: "var(--agent-reviewer)", message: "Approved changes with minor suggestions", time: "22s ago" },
  { agent: "Memory", color: "var(--agent-memory)", message: "Stored execution context to vector store", time: "28s ago" },
  { agent: "Supervisor", color: "var(--agent-supervisor)", message: "Completed workflow — all quality gates passed", time: "35s ago" },
];

/* ── Quick Action Cards ── */
const QUICK_ACTIONS = [
  { title: "Create Workflow", description: "Build and execute a multi-agent pipeline", href: "/workflows", icon: Workflow, accent: "var(--accent-primary)" },
  { title: "Ask the System", description: "Chat with your AI orchestration engine", href: "/chat", icon: MessageSquare, accent: "var(--accent-secondary)" },
  { title: "Explore Agents", description: "Inspect agent capabilities and activity", href: "/workflow-builder", icon: Bot, accent: "var(--accent-tertiary)" },
  { title: "View Executions", description: "Monitor running workflows in real-time", href: "/analytics", icon: Activity, accent: "var(--accent-success)" },
];

/* ── Animated Counter Hook ── */
function useCounter(target: number, duration: number = 2000) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = 0;
    const startTime = Date.now();
    const tick = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(tick);
    };
    const id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [target, duration]);
  return count;
}

/* ── Flow Pipeline Steps ── */
const FLOW_STEPS = [
  { label: "USER REQUEST", color: "var(--fg-primary)" },
  { label: "PLANNER", color: "var(--agent-planner)" },
  { label: "RESEARCHER", color: "var(--agent-researcher)" },
  { label: "CODER", color: "var(--agent-coder)" },
  { label: "TESTER", color: "var(--agent-tester)" },
  { label: "REVIEWER", color: "var(--agent-reviewer)" },
  { label: "MEMORY", color: "var(--agent-memory)" },
  { label: "SUPERVISOR", color: "var(--agent-supervisor)" },
  { label: "RESULT", color: "var(--accent-success)" },
];


export default function DashboardPage() {
  const { data, isLoading, isError, error, refetch, isFetching } =
    useSystemStatus();

  // Derive status
  const getStatus = (status?: string): "online" | "offline" | "loading" => {
    if (isLoading) return "loading";
    if (isError || !status) return "offline";
    return status === "connected" ? "online" : "offline";
  };

  const backendStatus = getStatus(data?.backend?.status);
  const dbStatus = getStatus(data?.database?.status);
  const ollamaStatus = isLoading ? "loading" : isError ? "offline" : getStatus(data?.ollama?.status);

  // Counters
  const totalRuns = useCounter(1248);
  const successRate = useCounter(986, 2500);
  const avgExecution = useCounter(241, 2000);
  const activeTasks = useCounter(34, 1500);

  return (
    <div style={{ background: "var(--bg-primary)", color: "var(--fg-primary)" }} className="min-h-screen flex flex-col">
      <AppNavbar />

      {/* ══════════════════════════════════════════════ */}
      {/* HERO SECTION                                  */}
      {/* ══════════════════════════════════════════════ */}
      <section className="blueprint-grid">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 lg:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left — Headline */}
            <div className="animate-fade-in-up">
              <div className="inline-block mb-6">
                <span className="brutalist-btn-primary text-caption px-3 py-1 border-2 border-[var(--border-primary)]"
                      style={{ boxShadow: "var(--shadow-brutalist-sm)" }}>
                  ENTERPRISE AI PLATFORM
                </span>
              </div>

              <h1 className="text-display mb-6" style={{ color: "var(--fg-primary)" }}>
                AI Agents.
                <br />
                <span style={{ color: "var(--accent-primary)" }}>Real Work.</span>
                <br />
                <span style={{ color: "var(--accent-secondary)" }}>Real Impact.</span>
              </h1>

              <p className="text-body max-w-lg mb-8" style={{ color: "var(--fg-secondary)" }}>
                Orchestrate specialized AI agents to automate complex workflows. Five execution agents (Planner, Researcher, Coder, Tester, Reviewer) collaborate under Orchestration Core supervision.
              </p>

              <div className="flex flex-wrap gap-3">
                <Link href="/app" className="brutalist-btn brutalist-btn-primary">
                  <Zap className="w-4 h-4" />
                  Open Command Center
                </Link>
                <Link href="/app/agents" className="brutalist-btn brutalist-btn-secondary">
                  <ArrowRight className="w-4 h-4" />
                  Explore 5 Agents
                </Link>
              </div>

              {/* Feature badges */}
              <div className="mt-10 flex flex-wrap gap-x-6 gap-y-3">
                {[
                  "Agent Orchestration",
                  "Workflow Automation",
                  "Real-time Analytics",
                  "Enterprise Security",
                ].map((f) => (
                  <div key={f} className="flex items-center gap-2">
                    <div className="status-dot status-dot-online" />
                    <span className="text-caption" style={{ color: "var(--fg-secondary)" }}>{f}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right — 3D Visualization */}
            <div className="animate-fade-in-up delay-2">
              <div className="relative border-2 border-[var(--border-primary)] h-[400px] lg:h-[450px]"
                   style={{ background: "var(--bg-surface)", boxShadow: "var(--shadow-brutalist-lg)" }}>
                <div className="absolute top-0 left-0 right-0 h-8 border-b-2 border-[var(--border-primary)] flex items-center px-3 gap-2"
                     style={{ background: "var(--bg-secondary)" }}>
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--accent-error)" }} />
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--accent-warning)" }} />
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--accent-success)" }} />
                  <span className="text-mono ml-2" style={{ color: "var(--fg-tertiary)", fontSize: "10px" }}>multiagent-core.render</span>
                </div>
                <div className="pt-8 h-full">
                  <Orchestration3D />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* SYSTEM PULSE                                  */}
      {/* ══════════════════════════════════════════════ */}
      <section className="border-t-2 border-[var(--border-primary)]" style={{ background: "var(--bg-surface)" }}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-h4" style={{ color: "var(--fg-primary)" }}>System Pulse</h2>
            <button onClick={() => refetch()} disabled={isFetching}
                    className="text-caption flex items-center gap-1.5 transition-colors"
                    style={{ color: "var(--fg-tertiary)" }}>
              <RefreshCw className={`w-3 h-3 ${isFetching ? "animate-spin" : ""}`} />
              {isFetching ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {/* Error state */}
          {isError && (
            <div className="mb-4 p-3 border-2 flex items-center gap-3"
                 style={{ borderColor: "var(--accent-error)", background: "rgba(239,68,68,0.05)" }}>
              <AlertTriangle className="w-4 h-4" style={{ color: "var(--accent-error)" }} />
              <span className="text-body-sm" style={{ color: "var(--accent-error)" }}>
                {error?.message || "Unable to reach backend"} — Ensure backend is running on localhost:8000
              </span>
              <button onClick={() => refetch()} disabled={isFetching}
                      className="ml-auto brutalist-btn brutalist-btn-secondary text-[10px] py-1 px-3">
                Retry
              </button>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Backend */}
            <PulseBlock label="BACKEND" value={backendStatus === "online" ? "ONLINE" : backendStatus === "loading" ? "..." : "OFFLINE"} status={backendStatus} />
            {/* Postgres */}
            <PulseBlock label="POSTGRES" value={dbStatus === "online" ? "ONLINE" : dbStatus === "loading" ? "..." : "OFFLINE"} status={dbStatus} />
            {/* Ollama */}
            <PulseBlock label="OLLAMA" value={ollamaStatus === "online" ? "ONLINE" : ollamaStatus === "loading" ? "..." : "OFFLINE"} status={ollamaStatus} />
            {/* Agents */}
            <PulseBlock label="AGENTS" value="5 / 5" status="online" />
            {/* Workflows */}
            <PulseBlock label="WORKFLOWS" value="ACTIVE" status="online" />
            {/* System */}
            <PulseBlock label="SYSTEM" value={data?.system_ready ? "99.9%" : isLoading ? "..." : "DEGRADED"} status={data?.system_ready ? "online" : isLoading ? "loading" : "offline"} />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* AGENT COMMAND CENTER                          */}
      {/* ══════════════════════════════════════════════ */}
      <section className="border-t-2 border-[var(--border-primary)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <h2 className="text-h1 mb-2 font-black tracking-tight">5 Specialized AI Execution Agents</h2>
          <p className="text-body-sm mb-8" style={{ color: "var(--fg-secondary)" }}>
            Five execution agents collaborate under Orchestration Core supervision to complete multi-step tasks.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {AGENTS.map((agent, i) => (
              <div key={agent.name}
                   className="brutalist-card p-4 animate-fade-in-up"
                   style={{ animationDelay: `${i * 80}ms` }}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 border-2 border-[var(--border-primary)] flex items-center justify-center"
                         style={{ background: agent.color }}>
                      <agent.icon className="w-4 h-4" style={{ color: "var(--fg-on-accent)" }} />
                    </div>
                    <span className="text-h4" style={{ color: "var(--fg-primary)" }}>{agent.name}</span>
                  </div>
                  <span className="text-caption font-bold px-2 py-0.5 border"
                        style={{
                          color: agent.status === "ACTIVE" ? "var(--accent-success)" : "var(--fg-tertiary)",
                          borderColor: agent.status === "ACTIVE" ? "var(--accent-success)" : "var(--border-secondary)",
                        }}>
                    {agent.status}
                  </span>
                </div>

                <p className="text-body-sm mb-3" style={{ color: "var(--fg-secondary)" }}>{agent.task}</p>

                {/* Workload bar */}
                <div className="mb-2">
                  <div className="flex justify-between mb-1">
                    <span className="text-caption" style={{ color: "var(--fg-tertiary)" }}>WORKLOAD</span>
                    <span className="text-caption font-bold" style={{ color: agent.color }}>{agent.workload}%</span>
                  </div>
                  <div className="h-1.5 w-full" style={{ background: "var(--bg-secondary)" }}>
                    <div className="h-full transition-all duration-1000"
                         style={{ width: `${agent.workload}%`, background: agent.color }} />
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <Clock className="w-3 h-3" style={{ color: "var(--fg-tertiary)" }} />
                  <span className="text-caption" style={{ color: "var(--fg-tertiary)" }}>{agent.lastAction}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* LIVE ORCHESTRATION FLOW                       */}
      {/* ══════════════════════════════════════════════ */}
      <section className="border-t-2 border-[var(--border-primary)]" style={{ background: "var(--bg-surface)" }}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <h2 className="text-h1 mb-2">Live Orchestration</h2>
          <p className="text-body-sm mb-8" style={{ color: "var(--fg-secondary)" }}>
            Watch how tasks flow through the agent pipeline — from user request to final result.
          </p>

          {/* Horizontal flow for desktop, vertical for mobile */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
            {FLOW_STEPS.map((step, i) => (
              <div key={step.label} className="flex items-center gap-2 sm:flex-col">
                <div className="w-full sm:w-auto">
                  <div className="brutalist-card-sm px-4 py-3 text-center min-w-[100px]"
                       style={{ borderColor: step.color }}>
                    <span className="text-caption font-bold" style={{ color: step.color }}>{step.label}</span>
                  </div>
                </div>
                {i < FLOW_STEPS.length - 1 && (
                  <div className="hidden sm:block">
                    <ArrowRight className="w-4 h-4" style={{ color: "var(--fg-tertiary)" }} />
                  </div>
                )}
                {i < FLOW_STEPS.length - 1 && (
                  <div className="sm:hidden w-0.5 h-4" style={{ background: "var(--border-secondary)" }} />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* PERFORMANCE METRICS                           */}
      {/* ══════════════════════════════════════════════ */}
      <section className="border-t-2 border-[var(--border-primary)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <h2 className="text-h1 mb-8">Orchestration Performance</h2>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              label="TOTAL RUNS"
              value={totalRuns.toLocaleString()}
              accent="var(--accent-primary)"
            />
            <MetricCard
              label="SUCCESS RATE"
              value={`${(successRate / 10).toFixed(1)}%`}
              accent="var(--accent-success)"
            />
            <MetricCard
              label="AVG EXECUTION"
              value={`${(avgExecution / 100).toFixed(2)}s`}
              accent="var(--accent-secondary)"
            />
            <MetricCard
              label="ACTIVE TASKS"
              value={activeTasks.toString()}
              accent="var(--accent-tertiary)"
            />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* LIVE ACTIVITY FEED                            */}
      {/* ══════════════════════════════════════════════ */}
      <section className="border-t-2 border-[var(--border-primary)]" style={{ background: "var(--bg-surface)" }}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <h2 className="text-h1 mb-2">Live Agent Activity</h2>
          <p className="text-body-sm mb-6" style={{ color: "var(--fg-secondary)" }}>
            Real-time feed of agent actions across your orchestration system.
          </p>

          <div className="space-y-2">
            {ACTIVITY_EVENTS.map((event, i) => (
              <div key={i}
                   className="flex items-start gap-3 p-3 border-2 border-[var(--border-secondary)] animate-fade-in-up"
                   style={{ animationDelay: `${i * 100}ms`, background: "var(--bg-primary)" }}>
                <div className="status-dot status-dot-online mt-1.5 shrink-0"
                     style={{ background: event.color, boxShadow: `0 0 6px ${event.color}` }} />
                <div className="flex-1 min-w-0">
                  <span className="text-caption font-bold mr-2" style={{ color: event.color }}>{event.agent}</span>
                  <span className="text-body-sm" style={{ color: "var(--fg-primary)" }}>{event.message}</span>
                </div>
                <span className="text-caption shrink-0" style={{ color: "var(--fg-tertiary)" }}>{event.time}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* COMMAND CENTER (QUICK ACTIONS)                */}
      {/* ══════════════════════════════════════════════ */}
      <section className="border-t-2 border-[var(--border-primary)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <h2 className="text-h1 mb-8">Command Center</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            {QUICK_ACTIONS.map((action) => (
              <Link key={action.href} href={action.href} className="group">
                <div className="brutalist-card p-6 h-full flex items-start gap-4">
                  <div className="w-10 h-10 border-2 border-[var(--border-primary)] flex items-center justify-center shrink-0"
                       style={{ background: action.accent }}>
                    <action.icon className="w-5 h-5" style={{ color: "var(--fg-on-accent)" }} />
                  </div>
                  <div>
                    <h3 className="text-h3 mb-1" style={{ color: "var(--fg-primary)" }}>{action.title}</h3>
                    <p className="text-body-sm" style={{ color: "var(--fg-secondary)" }}>{action.description}</p>
                  </div>
                  <ArrowRight className="w-5 h-5 ml-auto shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                              style={{ color: "var(--fg-tertiary)" }} />
                </div>
              </Link>
            ))}
          </div>

          {/* Secondary Actions Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Knowledge", href: "/knowledge", icon: FileText },
              { label: "Workspace", href: "/workspace", icon: Folder },
              { label: "Artifacts", href: "/artifacts", icon: Sparkles },
              { label: "Builder", href: "/workflow-builder", icon: Layers },
              { label: "Governance", href: "/governance", icon: ShieldCheck },
              { label: "AIOps", href: "/aiops", icon: Cpu },
            ].map((item) => (
              <Link key={item.href} href={item.href}>
                <div className="brutalist-card-sm p-3 text-center group hover:translate-x-[-2px] hover:translate-y-[-2px] transition-transform"
                     style={{ boxShadow: "var(--shadow-brutalist-sm)" }}>
                  <item.icon className="w-5 h-5 mx-auto mb-1.5" style={{ color: "var(--fg-secondary)" }} />
                  <span className="text-caption font-bold" style={{ color: "var(--fg-primary)" }}>{item.label}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════ */}
      {/* FINAL CTA                                     */}
      {/* ══════════════════════════════════════════════ */}
      <section className="border-t-2 border-[var(--border-primary)]"
               style={{ background: "var(--accent-primary)" }}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 text-center">
          <h2 className="text-h1 mb-4" style={{ color: "var(--fg-on-accent)" }}>
            Ready to Orchestrate?
          </h2>
          <p className="text-body max-w-xl mx-auto mb-8" style={{ color: "rgba(17,17,17,0.7)" }}>
            Deploy your first multi-agent workflow and experience the power of collaborative AI.
          </p>
          <Link href="/chat" className="brutalist-btn brutalist-btn-dark">
            <Zap className="w-4 h-4" />
            Launch AI Assistant
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <AppFooter />
    </div>
  );
}


/* ── Sub-components ── */

function PulseBlock({ label, value, status }: { label: string; value: string; status: "online" | "offline" | "loading" }) {
  return (
    <div className="brutalist-card-sm p-3">
      <div className="flex items-center gap-2 mb-1.5">
        <div className={`status-dot ${status === "online" ? "status-dot-online" : status === "offline" ? "status-dot-offline" : "status-dot-warning"}`} />
        <span className="text-caption" style={{ color: "var(--fg-tertiary)" }}>{label}</span>
      </div>
      <span className="text-h3 font-bold block"
            style={{ color: status === "online" ? "var(--accent-success)" : status === "offline" ? "var(--accent-error)" : "var(--fg-tertiary)" }}>
        {value}
      </span>
    </div>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="brutalist-card p-6 text-center">
      <span className="text-display block mb-2" style={{ color: accent, fontSize: "2.5rem" }}>{value}</span>
      <span className="text-h4" style={{ color: "var(--fg-secondary)" }}>{label}</span>
    </div>
  );
}
