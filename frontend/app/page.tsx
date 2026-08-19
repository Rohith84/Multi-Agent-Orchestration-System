/**
 * MultiAgent OS — Public Landing Page
 *
 * Premium marketing landing page with:
 * - Hero with 3D orchestration visualization
 * - Trust strip
 * - What is MultiAgent OS? (comparison)
 * - Agent showcase (7 agents)
 * - Orchestration architecture
 * - Platform capabilities
 * - Workflow Builder showcase
 * - Knowledge / RAG
 * - MCP Tools
 * - Enterprise governance
 * - Use cases
 * - Differentiators
 * - Final CTA
 * - Footer
 */

"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { PublicNavbar } from "@/components/public-navbar";
import { PublicFooter } from "@/components/public-footer";
import { useInView } from "@/hooks/use-in-view";
import {
  ArrowRight,
  ArrowDown,
  Zap,
  Brain,
  Search,
  Code,
  TestTube,
  CheckCircle,
  Database,
  Eye,
  Bot,
  MessageSquare,
  Workflow,
  Layers,
  FileText,
  Wrench,
  Folder,
  Sparkles,
  BarChart3,
  Activity,
  ShieldCheck,
  Users,
  Building2,
  Key,
  ClipboardList,
  Target,
  Network,
  Puzzle,
  Shield,
} from "lucide-react";

// Lazy-load 3D
const Orchestration3D = dynamic(
  () =>
    import("@/components/orchestration-3d").then((m) => ({
      default: m.Orchestration3D,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center">
        <div
          className="text-caption"
          style={{ color: "var(--fg-tertiary)" }}
        >
          Loading visualization...
        </div>
      </div>
    ),
  }
);

/* ── Section Wrapper with scroll-triggered reveal ── */
function RevealSection({
  children,
  id,
  className = "",
  style,
}: {
  children: React.ReactNode;
  id?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  const { ref, inView } = useInView({ threshold: 0.1 });
  return (
    <section
      ref={ref as React.Ref<HTMLElement>}
      id={id}
      className={`section-reveal ${inView ? "in-view" : ""} ${className}`}
      style={style}
    >
      {children}
    </section>
  );
}

/* ── Agent Definitions ── */
const AGENTS = [
  {
    name: "Planner",
    icon: Brain,
    color: "var(--agent-planner)",
    description: "Breaks complex objectives into structured execution plans.",
    role: "PLANNING",
    stepNum: "01",
  },
  {
    name: "Researcher",
    icon: Search,
    color: "var(--agent-researcher)",
    description: "Handles information gathering and contextual research.",
    role: "RESEARCH",
    stepNum: "02",
  },
  {
    name: "Coder",
    icon: Code,
    color: "var(--agent-coder)",
    description: "Handles implementation and software development tasks.",
    role: "IMPLEMENTATION",
    stepNum: "03",
  },
  {
    name: "Tester",
    icon: TestTube,
    color: "var(--agent-tester)",
    description: "Validates outputs and execution results.",
    role: "VALIDATION",
    stepNum: "04",
  },
  {
    name: "Reviewer",
    icon: CheckCircle,
    color: "var(--agent-reviewer)",
    description: "Reviews generated work for quality and correctness.",
    role: "QUALITY",
    stepNum: "05",
    isFinal: true,
  },
];

/* ── Orchestration Flow Steps ── */
const FLOW_STEPS = [
  { label: "USER INTENT", num: "01", color: "var(--fg-primary)" },
  { label: "PLANNING", num: "02", color: "var(--agent-planner)" },
  { label: "RESEARCH", num: "03", color: "var(--agent-researcher)" },
  { label: "CODING", num: "04", color: "var(--agent-coder)" },
  { label: "TESTING", num: "05", color: "var(--agent-tester)" },
  { label: "REVIEW", num: "06", color: "var(--agent-reviewer)" },
  { label: "RESULT", num: "07", color: "var(--accent-success)" },
];

/* ── Platform Capabilities ── */
const CAPABILITIES = [
  {
    title: "AI Assistant",
    description: "Multi-agent conversational execution",
    icon: MessageSquare,
    href: "/app/chat",
    accent: "var(--accent-primary)",
  },
  {
    title: "Workflow Center",
    description: "Create and monitor complex workflows",
    icon: Workflow,
    href: "/app/workflows",
    accent: "var(--accent-secondary)",
  },
  {
    title: "Workflow Builder",
    description: "Visual workflow construction",
    icon: Layers,
    href: "/app/workflow-builder",
    accent: "var(--accent-tertiary)",
  },
  {
    title: "Knowledge Base",
    description: "Document management and RAG indexing",
    icon: FileText,
    href: "/app/knowledge",
    accent: "var(--agent-memory)",
  },
  {
    title: "MCP Tools",
    description: "Discover and execute registered tools",
    icon: Wrench,
    href: "/app/tools",
    accent: "var(--agent-researcher)",
  },
  {
    title: "Autonomous Workspace",
    description: "Project files, testing and quality analysis",
    icon: Folder,
    href: "/app/workspace",
    accent: "var(--agent-planner)",
  },
  {
    title: "Artifact Studio",
    description: "Manage generated artifacts and versions",
    icon: Sparkles,
    href: "/app/artifacts",
    accent: "var(--accent-warning)",
  },
  {
    title: "Analytics",
    description: "Execution and system analytics",
    icon: BarChart3,
    href: "/app/analytics",
    accent: "var(--accent-success)",
  },
  {
    title: "Operations",
    description: "System health and operational monitoring",
    icon: Activity,
    href: "/app/operations",
    accent: "var(--accent-error)",
  },
  {
    title: "Governance",
    description: "Users, organizations, roles, API keys and audit logs",
    icon: ShieldCheck,
    href: "/app/governance",
    accent: "var(--agent-supervisor)",
  },
];

/* ── Use Cases ── */
const USE_CASES = [
  {
    title: "SOFTWARE DEVELOPMENT",
    flow: ["Research", "Code", "Test", "Review"],
    accent: "var(--agent-coder)",
  },
  {
    title: "RESEARCH AUTOMATION",
    flow: ["Plan", "Research", "Synthesize", "Review"],
    accent: "var(--agent-researcher)",
  },
  {
    title: "WORKFLOW AUTOMATION",
    flow: ["Intent", "Orchestration", "Execution", "Result"],
    accent: "var(--accent-primary)",
  },
  {
    title: "QUALITY ENGINEERING",
    flow: ["Generate", "Test", "Analyze", "Review"],
    accent: "var(--agent-tester)",
  },
];

/* ── Differentiators ── */
const DIFFERENTIATORS = [
  {
    title: "SPECIALIZED",
    description: "Different agents handle different responsibilities.",
    icon: Target,
  },
  {
    title: "ORCHESTRATED",
    description: "Agents collaborate through coordinated workflows.",
    icon: Network,
  },
  {
    title: "OBSERVABLE",
    description: "Execution can be monitored.",
    icon: Eye,
  },
  {
    title: "EXTENSIBLE",
    description: "Tools, knowledge and workflows connect into one platform.",
    icon: Puzzle,
  },
  {
    title: "GOVERNED",
    description: "Users, roles, API keys and audit capabilities are available.",
    icon: Shield,
  },
];

/* ── Trust Strip Items ── */
const TRUST_ITEMS = [
  "5 SPECIALIZED AGENTS",
  "REAL-TIME ORCHESTRATION",
  "WORKFLOW AUTOMATION",
  "RAG KNOWLEDGE",
  "MCP TOOLING",
  "ENTERPRISE GOVERNANCE",
];

export default function LandingPage() {
  return (
    <div
      style={{ background: "var(--bg-primary)", color: "var(--fg-primary)" }}
      className="min-h-screen flex flex-col"
    >
      <PublicNavbar />

      {/* ═══════════════════════════════════════════════ */}
      {/* HERO SECTION                                   */}
      {/* ═══════════════════════════════════════════════ */}
      <section className="blueprint-grid pt-24 sm:pt-28 lg:pt-32">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-12 lg:pb-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left — Headline */}
            <div className="animate-fade-in-up">
              <div className="inline-block mb-6">
                <span
                  className="brutalist-btn-primary text-caption px-3 py-1 border-2 border-[var(--border-primary)]"
                  style={{ boxShadow: "var(--shadow-brutalist-sm)" }}
                >
                  ENTERPRISE AI PLATFORM
                </span>
              </div>

              <h1
                className="text-display mb-6"
                style={{ color: "var(--fg-primary)" }}
              >
                One Intelligence Layer.
                <br />
                <span style={{ color: "var(--accent-text)" }}>
                  Five Specialized Agents.
                </span>
                <br />
                <span style={{ color: "var(--accent-secondary)" }}>
                  Infinite Workflows.
                </span>
              </h1>

              <p
                className="text-body max-w-lg mb-8"
                style={{ color: "var(--fg-secondary)" }}
              >
                MultiAgent OS is an enterprise multi-agent orchestration
                platform where five specialized AI agents collaborate to plan,
                research, build, test, and review complex workflows.
              </p>

              <div className="flex flex-wrap gap-3">
                <Link href="/app" className="brutalist-btn brutalist-btn-primary">
                  <Zap className="w-4 h-4" aria-hidden="true" />
                  Launch MultiAgent OS
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </Link>
                <a
                  href="#architecture"
                  onClick={(e) => {
                    e.preventDefault();
                    document
                      .getElementById("architecture")
                      ?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="brutalist-btn brutalist-btn-secondary"
                >
                  <ArrowDown className="w-4 h-4" aria-hidden="true" />
                  Explore the Architecture
                </a>
              </div>
            </div>

            {/* Right — 3D Visualization */}
            <div className="animate-fade-in-up delay-2">
              <div
                className="relative border-2 border-[var(--border-primary)] h-[350px] sm:h-[400px] lg:h-[450px]"
                style={{
                  background: "var(--bg-surface)",
                  boxShadow: "var(--shadow-brutalist-lg)",
                }}
              >
                <div
                  className="absolute top-0 left-0 right-0 h-8 border-b-2 border-[var(--border-primary)] flex items-center px-3 gap-2"
                  style={{ background: "var(--bg-secondary)" }}
                >
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: "var(--accent-error)" }}
                  />
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: "var(--accent-warning)" }}
                  />
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: "var(--accent-success)" }}
                  />
                  <span
                    className="text-mono ml-2"
                    style={{ color: "var(--fg-tertiary)", fontSize: "10px" }}
                  >
                    multiagent-core.render
                  </span>
                </div>
                <div className="pt-8 h-full">
                  <Orchestration3D />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════ */}
      {/* TRUST STRIP                                    */}
      {/* ═══════════════════════════════════════════════ */}
      <section
        className="border-t-2 border-b-2 border-[var(--border-primary)]"
        style={{ background: "var(--bg-surface)" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
            {TRUST_ITEMS.map((item) => (
              <div key={item} className="flex items-center gap-2">
                <div className="status-dot status-dot-online" />
                <span
                  className="text-caption font-bold"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════ */}
      {/* WHAT IS MULTIAGENT OS?                         */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection id="capabilities">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="text-center mb-12">
            <h2 className="text-h1 mb-3">
              AI That Works As A System.
              <br />
              <span style={{ color: "var(--accent-secondary)" }}>
                Not Just A Chatbot.
              </span>
            </h2>
            <p
              className="text-body max-w-2xl mx-auto"
              style={{ color: "var(--fg-secondary)" }}
            >
              Traditional AI gives you a single model responding to prompts.
              MultiAgent OS coordinates specialized agents that collaborate
              through structured workflows to deliver comprehensive results.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Traditional AI */}
            <div className="brutalist-card p-8 border-2 border-[var(--border-primary)]">
              <h3
                className="text-h4 font-black mb-6"
                style={{ color: "var(--fg-primary)" }}
              >
                TRADITIONAL AI
              </h3>
              <div className="space-y-4 text-center">
                {["User", "Single Model", "Response"].map((step, i) => (
                  <div key={step}>
                    <div
                      className="inline-block px-6 py-3 border-2 font-extrabold shadow-[var(--shadow-brutalist-sm)]"
                      style={{
                        borderColor: i === 1 ? "var(--accent-error)" : "var(--border-primary)",
                        background: i === 1 ? "var(--bg-surface)" : "var(--bg-secondary)",
                        color: "var(--fg-primary)",
                      }}
                    >
                      <span className="text-caption font-extrabold tracking-wide">
                        {step}
                      </span>
                    </div>
                    {i < 2 && (
                      <div className="flex justify-center my-2">
                        <ArrowDown
                          className="w-4 h-4"
                          style={{ color: "var(--fg-primary)" }}
                          aria-hidden="true"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* MultiAgent OS */}
            <div className="brutalist-card p-8 landing-glow-accent">
              <h3
                className="text-h4 mb-6"
                style={{ color: "var(--accent-text)" }}
              >
                MULTIAGENT OS
              </h3>
              <div className="space-y-3 text-center">
                {[
                  { label: "User", color: "var(--fg-primary)", bg: "var(--bg-surface)", fg: "var(--fg-primary)" },
                  { label: "Orchestrator", color: "var(--border-primary)", bg: "var(--accent-primary)", fg: "#111111" },
                  { label: "Planner", color: "var(--border-primary)", bg: "var(--agent-planner)", fg: "#111111" },
                  {
                    label: "Research / Coding / Testing",
                    color: "var(--agent-researcher)",
                    bg: "var(--bg-surface)",
                    fg: "var(--agent-researcher)",
                  },
                  { label: "Reviewer", color: "var(--agent-reviewer)", bg: "var(--bg-surface)", fg: "var(--agent-reviewer)" },
                  { label: "Final Result", color: "var(--accent-success)", bg: "var(--accent-success)", fg: "#111111" },
                ].map((step, i, arr) => (
                  <div key={step.label}>
                    <div
                      className="inline-block px-5 py-2.5 border-2 font-extrabold"
                      style={{
                        borderColor: step.color,
                        background: step.bg,
                        color: step.fg,
                      }}
                    >
                      <span className="text-caption font-extrabold tracking-wide">
                        {step.label}
                      </span>
                    </div>
                    {i < arr.length - 1 && (
                      <div className="flex justify-center my-1">
                        <ArrowDown
                          className="w-3 h-3"
                          style={{ color: step.color }}
                          aria-hidden="true"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* MEET THE AGENTS                                */}
      {/* ═══════════════════════════════════════════════ */}
      {/* ═══════════════════════════════════════════════ */}
      {/* MEET THE AGENTS                                */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection
        id="agents"
        className="border-t-2 border-[var(--border-primary)]"
        style={{ background: "var(--bg-surface)" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          {/* Header */}
          <div className="text-center mb-12">
            {/* Technical Pipeline Badge */}
            <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] shadow-[var(--shadow-brutalist-sm)]">
              <div className="w-2 h-2 rounded-full bg-[var(--accent-success)] status-dot-online" />
              <span className="text-caption font-bold tracking-wider uppercase text-[var(--fg-secondary)]">
                ORCHESTRATION PIPELINE • 5 SPECIALIZED AGENTS • SEQUENTIAL EXECUTION
              </span>
            </div>

            <h2 className="text-h1 mb-3">Meet the Agents</h2>
            <p
              className="text-body max-w-2xl mx-auto"
              style={{ color: "var(--fg-secondary)" }}
            >
              Five specialized agents collaborate under orchestration to complete complex multi-step tasks.
            </p>
          </div>

          {/* Execution Pipeline Container */}
          <div className="relative">
            {/* Cards Pipeline Grid: 1-col on mobile, 3-col on tablet (adapted), 5-col on desktop */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 lg:gap-3 items-stretch">
              {AGENTS.map((agent, i) => {
                const isLast = i === AGENTS.length - 1;
                return (
                  <div key={agent.name} className="relative flex flex-col group">
                    {/* Agent Card */}
                    <div
                      className="brutalist-card p-5 flex flex-col flex-1 relative transition-all duration-200 hover:-translate-y-1.5"
                      style={{
                        borderColor: "var(--border-primary)",
                      }}
                    >
                      {/* Top Header: Stage tag & Role badge */}
                      <div className="flex items-center justify-between mb-4 pb-2 border-b border-[var(--border-subtle)]">
                        <span
                          className="text-[10px] font-mono font-black px-2 py-0.5 border border-[var(--border-primary)] bg-[var(--bg-secondary)]"
                          style={{ color: "var(--fg-primary)" }}
                        >
                          STAGE {agent.stepNum}
                        </span>
                        <span
                          className="text-caption font-extrabold tracking-wider uppercase"
                          style={{ color: agent.color }}
                        >
                          {agent.role}
                        </span>
                      </div>

                      {/* Icon & Agent Title */}
                      <div className="flex items-center gap-3 mb-3">
                        <div
                          className="w-10 h-10 border-2 border-[var(--border-primary)] flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-110"
                          style={{
                            background: agent.color,
                            boxShadow: "var(--shadow-brutalist-sm)",
                          }}
                        >
                          <agent.icon
                            className="w-5 h-5"
                            style={{ color: "var(--fg-on-accent)" }}
                            aria-hidden="true"
                          />
                        </div>
                        <h3
                          className="text-h3 font-black"
                          style={{ color: "var(--fg-primary)" }}
                        >
                          {agent.name}
                        </h3>
                      </div>

                      {/* Description */}
                      <p
                        className="text-body-sm flex-1 mb-3"
                        style={{ color: "var(--fg-secondary)" }}
                      >
                        {agent.description}
                      </p>

                      {/* Final Stage Accent for Reviewer */}
                      {agent.isFinal && (
                        <div className="pt-2 border-t border-[var(--border-secondary)] flex items-center justify-between mt-auto">
                          <span className="text-[10px] font-extrabold uppercase tracking-wider text-[var(--accent-success)] flex items-center gap-1">
                            <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
                            FINAL VALIDATION
                          </span>
                          <span className="w-2 h-2 rounded-full bg-[var(--accent-success)] animate-pulse" />
                        </div>
                      )}
                    </div>

                    {/* Connector Arrow (Mobile vertical / Tablet adapt) */}
                    {!isLast && (
                      <div className="my-2 flex justify-center lg:hidden">
                        <div className="w-7 h-7 rounded-full border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] flex items-center justify-center shadow-[var(--shadow-brutalist-sm)]">
                          <ArrowDown className="w-3.5 h-3.5 text-[var(--fg-primary)] connector-pulse" aria-hidden="true" />
                        </div>
                      </div>
                    )}

                    {/* Desktop Connector Arrow overlay on right border for stages 1 to 4 */}
                    {!isLast && (
                      <div className="hidden lg:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10">
                        <div className="w-6 h-6 rounded-full border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] flex items-center justify-center shadow-[var(--shadow-brutalist-sm)] transition-transform group-hover:scale-110">
                          <ArrowRight className="w-3 h-3 text-[var(--fg-primary)] connector-pulse" aria-hidden="true" />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* HOW ORCHESTRATION WORKS                        */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection
        id="architecture"
        className="border-t-2 border-[var(--border-primary)]"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="text-center mb-12">
            <h2 className="text-h1 mb-3">How MultiAgent Orchestration Works</h2>
            <p
              className="text-body max-w-2xl mx-auto"
              style={{ color: "var(--fg-secondary)" }}
            >
              From user intent to final result — tasks flow through a
              structured pipeline of specialized agents.
            </p>
          </div>

          {/* Pipeline visualization */}
          <div className="max-w-3xl mx-auto">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {FLOW_STEPS.map((step, i) => (
                <div key={step.label} className="text-center">
                  <div
                    className="brutalist-card-sm p-4 mb-2"
                    style={{ borderColor: step.color }}
                  >
                    <span
                      className="text-caption block mb-1"
                      style={{ color: "var(--fg-tertiary)" }}
                    >
                      {step.num}
                    </span>
                    <span
                      className="text-caption font-bold block"
                      style={{ color: step.color }}
                    >
                      {step.label}
                    </span>
                  </div>
                  {i < FLOW_STEPS.length - 1 && (
                    <div className="flex justify-center sm:hidden py-1">
                      <ArrowDown
                        className="w-3 h-3 connector-pulse"
                        style={{ color: step.color }}
                        aria-hidden="true"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* PLATFORM CAPABILITIES                          */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection
        id="platform"
        className="border-t-2 border-[var(--border-primary)]"
        style={{ background: "var(--bg-surface)" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="text-center mb-12">
            <h2 className="text-h1 mb-3">Platform Capabilities</h2>
            <p
              className="text-body max-w-2xl mx-auto"
              style={{ color: "var(--fg-secondary)" }}
            >
              A complete enterprise AI operating system with integrated modules
              for every stage of intelligent workflow execution.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {CAPABILITIES.map((cap) => (
              <Link key={cap.href} href={cap.href} className="group">
                <div className="brutalist-card p-5 h-full flex flex-col">
                  <div
                    className="w-10 h-10 border-2 border-[var(--border-primary)] flex items-center justify-center mb-3"
                    style={{ background: cap.accent }}
                  >
                    <cap.icon
                      className="w-5 h-5"
                      style={{ color: "var(--fg-on-accent)" }}
                      aria-hidden="true"
                    />
                  </div>
                  <h3
                    className="text-h3 mb-1"
                    style={{ color: "var(--fg-primary)" }}
                  >
                    {cap.title}
                  </h3>
                  <p
                    className="text-body-sm flex-1"
                    style={{ color: "var(--fg-secondary)" }}
                  >
                    {cap.description}
                  </p>
                  <div className="mt-3 flex items-center gap-1">
                    <span
                      className="text-caption font-bold"
                      style={{ color: cap.accent }}
                    >
                      Explore
                    </span>
                    <ArrowRight
                      className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ color: cap.accent }}
                      aria-hidden="true"
                    />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* WORKFLOW BUILDER SHOWCASE                       */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection className="border-t-2 border-[var(--border-primary)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-h1 mb-4">
                Visual Workflow
                <br />
                <span style={{ color: "var(--accent-secondary)" }}>
                  Builder
                </span>
              </h2>
              <p
                className="text-body mb-6"
                style={{ color: "var(--fg-secondary)" }}
              >
                Design complex multi-agent workflows visually. Connect agents,
                define execution paths, and orchestrate intelligent pipelines
                without writing configuration code.
              </p>
              <Link
                href="/app/workflow-builder"
                className="brutalist-btn brutalist-btn-primary"
              >
                Build a Workflow
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>

            {/* Visual preview */}
            <div className="brutalist-card p-6 landing-glow-purple">
              <div className="space-y-2.5 text-center flex flex-col items-center">
                {[
                  { label: "TRIGGER", color: "var(--accent-primary)", fg: "#111111", icon: Zap },
                  { label: "PLANNER", color: "var(--agent-planner)", fg: "#111111", icon: Brain },
                  { label: "RESEARCH", color: "var(--agent-researcher)", fg: "#111111", icon: Search },
                  { label: "CODE", color: "var(--agent-coder)", fg: "#ffffff", icon: Code },
                  { label: "TEST", color: "var(--agent-tester)", fg: "#111111", icon: TestTube },
                  { label: "REVIEW", color: "var(--agent-reviewer)", fg: "#111111", icon: CheckCircle },
                  { label: "OUTPUT", color: "var(--accent-success)", fg: "#111111", icon: Sparkles },
                ].map((step, i, arr) => {
                  const IconComponent = step.icon;
                  return (
                    <div key={step.label} className="w-full flex flex-col items-center">
                      <div
                        className="inline-flex items-center justify-center gap-2 px-6 py-2 border-2 border-[var(--border-primary)] shadow-[var(--shadow-brutalist-sm)] transition-transform hover:scale-105 min-w-[160px]"
                        style={{
                          background: step.color,
                          color: step.fg,
                        }}
                      >
                        <IconComponent className="w-3.5 h-3.5" style={{ color: step.fg }} />
                        <span className="text-caption font-extrabold tracking-wide">
                          {step.label}
                        </span>
                      </div>
                      {i < arr.length - 1 && (
                        <div className="flex justify-center my-1">
                          <ArrowDown
                            className="w-3.5 h-3.5 connector-pulse"
                            style={{ color: step.color }}
                            aria-hidden="true"
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* KNOWLEDGE + RAG                                */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection
        className="border-t-2 border-[var(--border-primary)]"
        style={{ background: "var(--bg-surface)" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Visual */}
            <div className="brutalist-card p-6 landing-glow-cyan order-2 lg:order-1">
              <div className="space-y-2.5 text-center flex flex-col items-center">
                {[
                  { label: "DOCUMENT", color: "var(--fg-primary)", fg: "#ffffff", icon: FileText },
                  { label: "INGESTION", color: "var(--agent-researcher)", fg: "#111111", icon: Search },
                  { label: "CHUNKING", color: "var(--accent-tertiary)", fg: "#111111", icon: Layers },
                  { label: "VECTOR INDEX", color: "var(--agent-memory, var(--agent-coder))", fg: "#ffffff", icon: Database },
                  { label: "RETRIEVAL", color: "var(--agent-coder)", fg: "#ffffff", icon: Code },
                  { label: "AGENT CONTEXT", color: "var(--accent-success)", fg: "#111111", icon: Sparkles },
                ].map((step, i, arr) => {
                  const IconComponent = step.icon;
                  return (
                    <div key={step.label} className="w-full flex flex-col items-center">
                      <div
                        className="inline-flex items-center justify-center gap-2 px-6 py-2 border-2 border-[var(--border-primary)] shadow-[var(--shadow-brutalist-sm)] transition-transform hover:scale-105 min-w-[200px]"
                        style={{
                          background: step.color,
                          color: step.fg,
                        }}
                      >
                        <IconComponent className="w-3.5 h-3.5" style={{ color: step.fg }} />
                        <span className="text-caption font-extrabold tracking-wide">
                          {step.label}
                        </span>
                      </div>
                      {i < arr.length - 1 && (
                        <div className="flex justify-center my-1">
                          <ArrowDown
                            className="w-3.5 h-3.5 connector-pulse"
                            style={{ color: step.color }}
                            aria-hidden="true"
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="order-1 lg:order-2">
              <h2 className="text-h1 mb-4">
                Knowledge Base
                <br />
                <span style={{ color: "var(--accent-tertiary)" }}>
                  & RAG Pipeline
                </span>
              </h2>
              <p
                className="text-body mb-6"
                style={{ color: "var(--fg-secondary)" }}
              >
                Index documents into a vector store for retrieval-augmented
                generation. Agents automatically access relevant context from
                your knowledge base during workflow execution.
              </p>
              <Link
                href="/app/knowledge"
                className="brutalist-btn brutalist-btn-primary"
              >
                Explore Knowledge Base
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* MCP TOOLS                                      */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection className="border-t-2 border-[var(--border-primary)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-h1 mb-4">
                MCP Tool
                <br />
                <span style={{ color: "var(--agent-researcher)" }}>
                  Registry
                </span>
              </h2>
              <p
                className="text-body mb-6"
                style={{ color: "var(--fg-secondary)" }}
              >
                Agents access a unified tool registry through the Model Context
                Protocol. Discover available tools, execute them during
                workflows, and audit execution history.
              </p>
              <Link
                href="/app/tools"
                className="brutalist-btn brutalist-btn-primary"
              >
                Explore MCP Tools
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            </div>

            {/* Visual */}
            <div className="brutalist-card p-6 landing-glow-cyan">
              <div className="space-y-2.5 text-center flex flex-col items-center">
                {[
                  { label: "AI AGENTS", color: "var(--agent-coder)", fg: "#ffffff", icon: Bot },
                  { label: "MCP TOOL REGISTRY", color: "var(--accent-primary)", fg: "#111111", icon: Wrench },
                  { label: "AVAILABLE TOOLS", color: "var(--agent-researcher)", fg: "#111111", icon: Puzzle },
                  { label: "EXECUTION", color: "var(--accent-secondary)", fg: "#111111", icon: Zap },
                  { label: "AUDIT HISTORY", color: "var(--agent-supervisor, var(--fg-primary))", fg: "#ffffff", icon: ShieldCheck },
                ].map((step, i, arr) => {
                  const IconComponent = step.icon;
                  return (
                    <div key={step.label} className="w-full flex flex-col items-center">
                      <div
                        className="inline-flex items-center justify-center gap-2 px-6 py-2 border-2 border-[var(--border-primary)] shadow-[var(--shadow-brutalist-sm)] transition-transform hover:scale-105 min-w-[200px]"
                        style={{
                          background: step.color,
                          color: step.fg,
                        }}
                      >
                        <IconComponent className="w-3.5 h-3.5" style={{ color: step.fg }} />
                        <span className="text-caption font-extrabold tracking-wide">
                          {step.label}
                        </span>
                      </div>
                      {i < arr.length - 1 && (
                        <div className="flex justify-center my-1">
                          <ArrowDown
                            className="w-3.5 h-3.5 connector-pulse"
                            style={{ color: step.color }}
                            aria-hidden="true"
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* ENTERPRISE GOVERNANCE                          */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection
        id="governance"
        className="border-t-2 border-[var(--border-primary)]"
        style={{ background: "var(--bg-surface)" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="text-center mb-12">
            <h2 className="text-h1 mb-3">Enterprise Governance</h2>
            <p
              className="text-body max-w-2xl mx-auto"
              style={{ color: "var(--fg-secondary)" }}
            >
              Built-in identity, access, and audit capabilities for enterprise
              deployment.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 max-w-4xl mx-auto">
            {[
              { label: "Users", icon: Users },
              { label: "Organizations", icon: Building2 },
              { label: "Teams", icon: Bot },
              { label: "Roles", icon: ShieldCheck },
              { label: "API Keys", icon: Key },
              { label: "Audit Logs", icon: ClipboardList },
            ].map((item) => (
              <div
                key={item.label}
                className="brutalist-card-sm p-4 text-center"
              >
                <item.icon
                  className="w-6 h-6 mx-auto mb-2"
                  style={{ color: "var(--fg-secondary)" }}
                  aria-hidden="true"
                />
                <span
                  className="text-caption font-bold block"
                  style={{ color: "var(--fg-primary)" }}
                >
                  {item.label}
                </span>
              </div>
            ))}
          </div>

          <div className="text-center mt-8">
            <Link
              href="/app/governance"
              className="brutalist-btn brutalist-btn-secondary"
            >
              Explore Governance
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* USE CASES                                      */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection className="border-t-2 border-[var(--border-primary)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="text-center mb-12">
            <h2 className="text-h1 mb-3">Use Cases</h2>
            <p
              className="text-body max-w-2xl mx-auto"
              style={{ color: "var(--fg-secondary)" }}
            >
              Example scenarios where multi-agent orchestration delivers
              structured, reliable results.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-4xl mx-auto">
            {USE_CASES.map((uc) => (
              <div key={uc.title} className="brutalist-card p-6">
                <h3
                  className="text-h4 mb-4"
                  style={{ color: uc.accent }}
                >
                  {uc.title}
                </h3>
                <div className="flex items-center gap-2 flex-wrap">
                  {uc.flow.map((step, i) => (
                    <div key={step} className="flex items-center gap-2">
                      <span
                        className="text-caption font-bold px-3 py-1 border-2 border-[var(--border-secondary)]"
                        style={{ color: "var(--fg-primary)" }}
                      >
                        {step}
                      </span>
                      {i < uc.flow.length - 1 && (
                        <ArrowRight
                          className="w-3 h-3"
                          style={{ color: "var(--fg-tertiary)" }}
                          aria-hidden="true"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* WHY MULTIAGENT OS?                             */}
      {/* ═══════════════════════════════════════════════ */}
      <RevealSection
        className="border-t-2 border-[var(--border-primary)]"
        style={{ background: "var(--bg-surface)" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="text-center mb-12">
            <h2 className="text-h1 mb-3">Why MultiAgent OS?</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {DIFFERENTIATORS.map((d) => (
              <div key={d.title} className="brutalist-card p-5 text-center">
                <d.icon
                  className="w-8 h-8 mx-auto mb-3"
                  style={{ color: "var(--accent-primary)" }}
                  aria-hidden="true"
                />
                <h3
                  className="text-h4 mb-2"
                  style={{ color: "var(--fg-primary)" }}
                >
                  {d.title}
                </h3>
                <p
                  className="text-body-sm"
                  style={{ color: "var(--fg-secondary)" }}
                >
                  {d.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* ═══════════════════════════════════════════════ */}
      {/* FINAL CTA                                      */}
      {/* ═══════════════════════════════════════════════ */}
      <section
        className="border-t-2 border-[var(--border-primary)]"
        style={{ background: "var(--accent-primary)" }}
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20 text-center">
          <h2
            className="text-h1 mb-2"
            style={{ color: "var(--fg-on-accent)" }}
          >
            The Next Generation
          </h2>
          <h2
            className="text-h1 mb-6"
            style={{ color: "var(--fg-on-accent)", opacity: 0.8 }}
          >
            Of AI Workflows Starts Here.
          </h2>
          <p
            className="text-body max-w-xl mx-auto mb-8"
            style={{ color: "rgba(17,17,17,0.7)" }}
          >
            Turn complex tasks into coordinated intelligence.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link href="/app" className="brutalist-btn brutalist-btn-dark">
              <Zap className="w-4 h-4" aria-hidden="true" />
              Launch MultiAgent OS
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            <Link
              href="/login"
              className="text-sm font-bold uppercase tracking-wide underline underline-offset-4"
              style={{ color: "var(--fg-on-accent)" }}
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
