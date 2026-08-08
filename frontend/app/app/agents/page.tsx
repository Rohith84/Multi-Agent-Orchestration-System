/**
 * /app/agents — Agent Control Center.
 *
 * Dedicated control panel for the 5 AI Execution Agents:
 * - 01 PLANNER
 * - 02 RESEARCHER
 * - 03 CODER
 * - 04 TESTER
 * - 05 REVIEWER
 *
 * Plus dedicated panels for:
 * - SUPERVISOR (Orchestration Core — Control Layer)
 * - MEMORY (Platform RAG & State Store)
 *
 * Model names are rendered dynamically only when retrieved from backend context,
 * otherwise displaying "Model not configured" or "Not available".
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Brain,
  Search,
  Code,
  TestTube,
  CheckCircle,
  Eye,
  Database,
  ArrowRight,
  Zap,
  Clock,
  Shield,
  Layers,
  Cpu,
  RefreshCw,
} from "lucide-react";
import { useSystemStatus } from "@/hooks/use-system-status";

interface AgentSpec {
  id: string;
  number: string;
  name: string;
  role: string;
  icon: any;
  color: string;
  capabilities: string[];
  // Model is dynamic — if retrieved from backend config/API state it displays, otherwise fallback
  configuredModel?: string | null;
  status: "IDLE" | "RUNNING" | "WAITING" | "COMPLETED" | "FAILED" | "RETRYING";
}

const FIVE_EXECUTION_AGENTS: AgentSpec[] = [
  {
    id: "planner",
    number: "01",
    name: "PLANNER",
    role: "Strategic Task Decomposition",
    icon: Brain,
    color: "var(--agent-planner)",
    capabilities: [
      "Breaks user intent into structured JSON execution graph",
      "Assigns sub-tasks to downstream specialized agents",
      "Evaluates prerequisite constraints and dependency order",
    ],
    configuredModel: null, // Will display "Not available" unless backend passes it
    status: "IDLE",
  },
  {
    id: "researcher",
    number: "02",
    name: "RESEARCHER",
    role: "Web Search & Context Retrieval",
    icon: Search,
    color: "var(--agent-researcher)",
    capabilities: [
      "Performs real-time web searches and document fetches",
      "Retrieves indexed context from PostgreSQL vector store",
      "Synthesizes external documentation into structured prompts",
    ],
    configuredModel: null,
    status: "IDLE",
  },
  {
    id: "coder",
    number: "03",
    name: "CODER",
    role: "Code Synthesis & Implementation",
    icon: Code,
    color: "var(--agent-coder)",
    capabilities: [
      "Generates clean, typed Python and TypeScript code",
      "Modifies workspace files with atomic diff patches",
      "Integrates with MCP tool registry for filesystem operations",
    ],
    configuredModel: null,
    status: "IDLE",
  },
  {
    id: "tester",
    number: "04",
    name: "TESTER",
    role: "Automated Verification & Test Execution",
    icon: TestTube,
    color: "var(--agent-tester)",
    capabilities: [
      "Executes pytest suites inside isolated sandbox environment",
      "Parses stdout/stderr for assertion errors and tracebacks",
      "Reports failing test suites back to Orchestration Core for repair",
    ],
    configuredModel: null,
    status: "IDLE",
  },
  {
    id: "reviewer",
    number: "05",
    name: "REVIEWER",
    role: "Quality Gate & Security Inspection",
    icon: CheckCircle,
    color: "var(--agent-reviewer)",
    capabilities: [
      "Audits generated code against security standards and linters",
      "Evaluates overall completeness, grounding, and accuracy",
      "Approve or flags code for automated self-repair loop",
    ],
    configuredModel: null,
    status: "IDLE",
  },
];

export default function AgentControlCenterPage() {
  const { data, isLoading, refetch } = useSystemStatus();

  return (
    <div className="space-y-10 max-w-7xl mx-auto">

      {/* Page Header */}
      <div className="p-6 brutalist-card flex flex-col md:flex-row md:items-center justify-between gap-4"
           style={{ background: "var(--bg-surface)" }}>
        <div>
          <div className="inline-block mb-2">
            <span className="brutalist-btn-primary text-caption px-2.5 py-0.5 border"
                  style={{ borderColor: "var(--border-primary)" }}>
              EXECUTION MATRIX
            </span>
          </div>
          <h1 className="text-h1 font-black tracking-tight" style={{ color: "var(--fg-primary)" }}>
            Agent Control Center
          </h1>
          <p className="text-body-sm mt-1 max-w-2xl" style={{ color: "var(--fg-secondary)" }}>
            Inspect the five specialized AI execution agents. Task routing, retries, and workflow state are managed by the Supervisor Orchestration Core.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="brutalist-btn brutalist-btn-secondary text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <Link href="/app/chat" className="brutalist-btn brutalist-btn-primary text-xs">
            <Zap className="w-3.5 h-3.5" />
            Launch Workflow
          </Link>
        </div>
      </div>

      {/* ══════════════════════════════════════════════ */}
      {/* SECTION: 5 AI EXECUTION AGENTS GRID           */}
      {/* ══════════════════════════════════════════════ */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-h2 font-black uppercase tracking-tight" style={{ color: "var(--fg-primary)" }}>
              01 — 05 Execution Agents
            </h2>
            <p className="text-body-sm" style={{ color: "var(--fg-secondary)" }}>
              Specialized execution roles. Each agent performs an explicit step in the autonomous pipeline.
            </p>
          </div>
          <span className="text-caption font-bold px-3 py-1 border-2 border-[var(--border-primary)] bg-[var(--accent-primary)] text-[var(--fg-on-accent)]">
            5 AGENTS ACTIVE
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {FIVE_EXECUTION_AGENTS.map((agent) => (
            <div
              key={agent.id}
              className="brutalist-card p-5 flex flex-col justify-between"
              style={{ background: "var(--bg-surface)" }}
            >
              <div>
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                  <span className="text-mono font-black text-lg" style={{ color: agent.color }}>
                    {agent.number}
                  </span>
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 border"
                        style={{
                          color: "var(--accent-success)",
                          borderColor: "var(--accent-success)",
                        }}>
                    {agent.status}
                  </span>
                </div>

                {/* Name & Icon */}
                <div className="flex items-center gap-2.5 mb-2">
                  <div className="w-8 h-8 border-2 border-[var(--border-primary)] flex items-center justify-center shrink-0"
                       style={{ background: agent.color }}>
                    <agent.icon className="w-4 h-4" style={{ color: "var(--fg-on-accent)" }} />
                  </div>
                  <div>
                    <h3 className="text-sm font-extrabold uppercase" style={{ color: "var(--fg-primary)" }}>
                      {agent.name}
                    </h3>
                    <p className="text-[10px] font-mono" style={{ color: "var(--fg-tertiary)" }}>
                      {agent.role}
                    </p>
                  </div>
                </div>

                {/* Dynamic Model Assignment */}
                <div className="my-3 p-2 border border-[var(--border-secondary)] bg-[var(--bg-secondary)]">
                  <span className="text-[9px] font-bold uppercase tracking-wider block text-[var(--fg-tertiary)]">
                    MODEL ASSIGNMENT
                  </span>
                  <span className="text-xs font-mono font-bold block truncate"
                        style={{ color: agent.configuredModel ? "var(--fg-primary)" : "var(--fg-tertiary)" }}>
                    {agent.configuredModel || "Not configured"}
                  </span>
                </div>

                {/* Capabilities */}
                <div className="space-y-1.5 my-4">
                  <span className="text-[9px] font-bold uppercase tracking-wider block text-[var(--fg-tertiary)]">
                    CAPABILITIES
                  </span>
                  {agent.capabilities.map((cap, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-caption" style={{ color: "var(--fg-secondary)" }}>
                      <span className="text-[var(--accent-secondary)] font-bold">•</span>
                      <span>{cap}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Card Footer */}
              <div className="pt-3 border-t border-[var(--border-secondary)] flex items-center justify-between text-[10px] text-[var(--fg-tertiary)]">
                <span>Latency: --</span>
                <span>Success: --</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ══════════════════════════════════════════════ */}
      {/* SECTION: ORCHESTRATION CORE (SUPERVISOR)      */}
      {/* ══════════════════════════════════════════════ */}
      <div className="brutalist-card p-6" style={{ background: "var(--bg-surface)" }}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 border-b-2 border-[var(--border-primary)] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 border-2 border-[var(--border-primary)] bg-[var(--fg-primary)] flex items-center justify-center">
              <Eye className="w-5 h-5 text-[var(--fg-inverted)]" />
            </div>
            <div>
              <span className="text-caption font-bold text-[var(--accent-secondary)] uppercase tracking-wider block">
                CONTROL LAYER
              </span>
              <h2 className="text-h2 font-black uppercase tracking-tight" style={{ color: "var(--fg-primary)" }}>
                Supervisor / Orchestration Core
              </h2>
            </div>
          </div>
          <span className="text-caption font-mono border px-3 py-1 text-[var(--fg-secondary)] border-[var(--border-secondary)]">
            SYSTEM LAYER — NOT AN AGENT
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase text-[var(--fg-primary)]">Task Routing & Dispatch</h4>
            <p className="text-body-sm text-[var(--fg-secondary)]">
              Receives user requests, passes state to Planner, and dispatches sub-tasks to specialized agents based on execution dependency order.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase text-[var(--fg-primary)]">Self-Repair & Failure Loops</h4>
            <p className="text-body-sm text-[var(--fg-secondary)]">
              When Tester detects failing tests or Reviewer flags issues, Orchestration Core feeds failure logs back into Coder for automatic code repair loops.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase text-[var(--fg-primary)]">Human-in-the-Loop (HITL)</h4>
            <p className="text-body-sm text-[var(--fg-secondary)]">
              Pauses execution at configured approval gates, preserving checkpoint states until approved or rejected by human operators.
            </p>
          </div>
        </div>

        {/* Visual Pipeline Schematic */}
        <div className="mt-8 p-4 border-2 border-[var(--border-primary)] bg-[var(--bg-secondary)]">
          <span className="text-caption font-bold uppercase block mb-3 text-[var(--fg-tertiary)]">
            ORCHESTRATION DISPATCH FLOW
          </span>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono font-bold">
            <div className="px-3 py-1.5 border-2 bg-[var(--bg-surface)] border-[var(--border-primary)] text-[var(--fg-primary)]">
              SUPERVISOR CORE
            </div>
            <span>→</span>
            <div className="px-3 py-1.5 border-2 bg-[var(--bg-surface)] border-[var(--agent-planner)] text-[var(--agent-planner)]">
              01 PLANNER
            </div>
            <span>→</span>
            <div className="px-3 py-1.5 border-2 bg-[var(--bg-surface)] border-[var(--agent-researcher)] text-[var(--agent-researcher)]">
              02 RESEARCHER
            </div>
            <span>→</span>
            <div className="px-3 py-1.5 border-2 bg-[var(--bg-surface)] border-[var(--agent-coder)] text-[var(--agent-coder)]">
              03 CODER
            </div>
            <span>→</span>
            <div className="px-3 py-1.5 border-2 bg-[var(--bg-surface)] border-[var(--agent-tester)] text-[var(--agent-tester)]">
              04 TESTER
            </div>
            <span>→</span>
            <div className="px-3 py-1.5 border-2 bg-[var(--bg-surface)] border-[var(--agent-reviewer)] text-[var(--agent-reviewer)]">
              05 REVIEWER
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════ */}
      {/* SECTION: MEMORY & RAG CAPABILITY              */}
      {/* ══════════════════════════════════════════════ */}
      <div className="brutalist-card p-6" style={{ background: "var(--bg-surface)" }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 border-2 border-[var(--border-primary)] bg-[var(--agent-memory)] flex items-center justify-center">
            <Database className="w-4 h-4 text-[var(--fg-on-accent)]" />
          </div>
          <div>
            <span className="text-caption font-bold text-[var(--agent-memory)] uppercase tracking-wider block">
              PLATFORM CAPABILITY
            </span>
            <h3 className="text-h3 font-black uppercase" style={{ color: "var(--fg-primary)" }}>
              Memory & Knowledge Vector Store
            </h3>
          </div>
        </div>
        <p className="text-body-sm text-[var(--fg-secondary)] max-w-3xl">
          Memory is an infrastructure capability powered by PostgreSQL (`multi_agent_db`), ChromaDB embeddings, and LangGraph state checkpoints. It provides long-term context, document chunk retrieval (RAG), and shared execution thread state across all five agents.
        </p>
      </div>

    </div>
  );
}
