/**
 * /app/workflows/[id] — Workflow Execution & Checkpoint Center.
 *
 * Dedicated real-time execution monitoring page for an individual workflow.
 * Features:
 * - Real detail fetching from GET /api/workflows/{id}
 * - Reuses fetch + ReadableStream SSE stream decoder for live execution events
 * - Dynamic 5-Agent Execution Graph driven by backend state/events
 * - Human Approval Required Gate (Approve & Reject with comment input)
 * - Data-driven Checkpoint Inspector (Shared State, Tool History, Research Context)
 * - Structured split-view: Left = Event Stream Log, Right = Execution State & Inspector
 * - Links to /app/artifacts, /app/workspace, /app/agents
 */

"use client";

import { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type {
  WorkflowDetail,
  WorkflowCheckpoint,
  WorkflowApproval,
} from "@/services/workflows-service";
import {
  fetchWorkflowDetail,
  approveWorkflowStage,
  rejectWorkflowStage,
  resumeWorkflow,
  cancelWorkflow,
  restartWorkflow,
} from "@/services/workflows-service";
import {
  Brain,
  Search,
  Code,
  TestTube,
  CheckCircle,
  Eye,
  Database,
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  Play,
  RotateCcw,
  XCircle,
  Clock,
  ShieldAlert,
  Check,
  X,
  FileCode,
  Folder,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

interface SSEEventItem {
  id: string;
  timestamp: string;
  event: string;
  agent?: string;
  output?: string;
  error?: string;
  toolName?: string;
  executionTime?: number;
  message?: string;
}

const AGENTS_LIST = [
  { name: "planner", number: "01", label: "PLANNER", icon: Brain, color: "var(--agent-planner)" },
  { name: "research", number: "02", label: "RESEARCHER", icon: Search, color: "var(--agent-researcher)" },
  { name: "coder", number: "03", label: "CODER", icon: Code, color: "var(--agent-coder)" },
  { name: "tester", number: "04", label: "TESTER", icon: TestTube, color: "var(--agent-tester)" },
  { name: "reviewer", number: "05", label: "REVIEWER", icon: CheckCircle, color: "var(--agent-reviewer)" },
];

export default function WorkflowExecutionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: workflowId } = use(params);
  const router = useRouter();

  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Human Approval State
  const [approvalComment, setApprovalComment] = useState("");

  // Live SSE Event Stream Items
  const [eventStream, setEventStream] = useState<SSEEventItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Inspector Active Tab
  const [activeTab, setActiveTab] = useState<"state" | "tools" | "research" | "chat">("state");

  // Fetch workflow detail from backend
  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWorkflowDetail(workflowId);
      setDetail(data);

      // Populate initial events from checkpoints if available
      if (data.checkpoints && data.checkpoints.length > 0) {
        const initialEvents: SSEEventItem[] = data.checkpoints.map((cp, idx) => ({
          id: cp.id || `cp-${idx}`,
          timestamp: new Date(cp.created_at).toLocaleTimeString(),
          event: "agent_checkpoint",
          agent: cp.agent_name,
          output: `Saved checkpoint state for ${cp.agent_name}`,
        }));
        setEventStream((prev) => (prev.length === 0 ? initialEvents : prev));
      }
    } catch (err: any) {
      console.error("Failed to load workflow detail:", err);
      setError(err?.message || "Failed to load workflow execution state.");
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  // Handle Human Approval Gate
  const handleApprove = async () => {
    if (actionLoading || !detail) return;
    setActionLoading(true);
    try {
      const updated = await approveWorkflowStage(workflowId, approvalComment);
      setDetail(updated);
      setApprovalComment("");
      // Resume execution stream
      await handleResumeStream();
    } catch (err: any) {
      console.error("Failed to approve workflow stage:", err);
      alert(`Approval error: ${err?.message || "Failed to approve"}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (actionLoading || !detail) return;
    setActionLoading(true);
    try {
      const updated = await rejectWorkflowStage(workflowId, approvalComment);
      setDetail(updated);
      setApprovalComment("");
    } catch (err: any) {
      console.error("Failed to reject workflow stage:", err);
      alert(`Rejection error: ${err?.message || "Failed to reject"}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Resume Execution Stream
  const handleResumeStream = async () => {
    setIsStreaming(true);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${API_URL}/api/workflows/${workflowId}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;

          const jsonStr = trimmed.replace("data: ", "");
          try {
            const data = JSON.parse(jsonStr);
            const newEvent: SSEEventItem = {
              id: `evt-${Date.now()}-${Math.random()}`,
              timestamp: new Date().toLocaleTimeString(),
              event: data.event,
              agent: data.agent,
              output: data.output,
              error: data.error,
              toolName: data.tool_name,
              executionTime: data.execution_time,
              message: data.message,
            };

            setEventStream((prev) => [newEvent, ...prev]);

            if (data.event === "workflow_complete" || data.event === "workflow_failed") {
              loadDetail();
            }
          } catch (e) {
            console.error("Error parsing stream chunk:", e);
          }
        }
      }
    } catch (err: any) {
      console.error("Stream execution error:", err);
    } finally {
      setIsStreaming(false);
      loadDetail();
    }
  };

  const handleCancelAction = async () => {
    if (!detail) return;
    try {
      const updated = await cancelWorkflow(workflowId);
      setDetail(updated);
    } catch (err) {
      console.error("Cancel failed:", err);
    }
  };

  const handleRestartAction = async () => {
    if (!detail) return;
    try {
      const updated = await restartWorkflow(workflowId);
      setDetail(updated);
      handleResumeStream();
    } catch (err) {
      console.error("Restart failed:", err);
    }
  };

  // Determine agent status in graph dynamically from backend detail/events
  const getAgentGraphStatus = (agentName: string) => {
    if (!detail) return "WAITING";
    if (detail.current_agent === agentName) {
      if (detail.status === "paused_approval") return "PAUSED_APPROVAL";
      if (detail.status === "running") return "RUNNING";
      if (detail.status === "failed") return "FAILED";
    }

    const checkpoint = detail.checkpoints?.find((cp) => cp.agent_name === agentName);
    if (checkpoint) return "COMPLETED";

    if (detail.status === "completed" || detail.status === "failed" || detail.status === "cancelled") {
      return "NOT USED";
    }
    return "WAITING";
  };

  // Active Checkpoint
  const activeCheckpoint = detail?.checkpoints && detail.checkpoints.length > 0
    ? detail.checkpoints[detail.checkpoints.length - 1]
    : null;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">

      {/* Top Header */}
      <div className="p-6 brutalist-card flex flex-col lg:flex-row lg:items-center justify-between gap-4"
           style={{ background: "var(--bg-surface)" }}>
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link
              href="/app/workflows"
              className="p-1.5 border-2 border-[var(--border-primary)] hover:bg-[var(--accent-primary)] transition-colors"
              title="Back to Workflows"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1 className="text-h1 font-black tracking-tight truncate max-w-xl" style={{ color: "var(--fg-primary)" }}>
              {detail?.title || "Workflow Execution"}
            </h1>
          </div>
          <p className="text-mono text-xs text-[var(--fg-tertiary)] flex flex-wrap items-center gap-2 pt-1">
            <span>UUID: {workflowId}</span>
            <span>•</span>
            <span>Started: {detail ? new Date(detail.created_at).toLocaleString() : "--"}</span>
            {detail?.execution_time && (
              <>
                <span>•</span>
                <span className="text-[var(--accent-secondary)] font-bold">Duration: {detail.execution_time.toFixed(1)}s</span>
              </>
            )}
          </p>
        </div>

        {/* Actions & Status Badge */}
        <div className="flex flex-wrap items-center gap-3">
          {detail && (
            <span className="text-xs font-black uppercase px-3 py-1 border-2"
                  style={{
                    color: getStatusColor(detail.status),
                    borderColor: getStatusColor(detail.status),
                  }}>
              STATUS: {detail.status.replace("_", " ")}
            </span>
          )}

          {detail?.status === "paused_approval" && (
            <button
              onClick={handleResumeStream}
              disabled={isStreaming}
              className="brutalist-btn brutalist-btn-primary text-xs"
            >
              <Play className="w-3.5 h-3.5" />
              Resume Stream
            </button>
          )}

          {detail?.status === "running" && (
            <button
              onClick={handleCancelAction}
              className="brutalist-btn brutalist-btn-secondary text-xs"
            >
              <XCircle className="w-3.5 h-3.5 text-[var(--accent-error)]" />
              Cancel
            </button>
          )}

          {(detail?.status === "failed" || detail?.status === "completed") && (
            <button
              onClick={handleRestartAction}
              className="brutalist-btn brutalist-btn-secondary text-xs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Restart
            </button>
          )}

          <button onClick={loadDetail} className="brutalist-btn brutalist-btn-secondary text-xs">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 border-2 flex items-center gap-3"
             style={{ borderColor: "var(--accent-error)", background: "rgba(239,68,68,0.05)" }}>
          <AlertTriangle className="w-5 h-5 shrink-0" style={{ color: "var(--accent-error)" }} />
          <div className="flex-1">
            <p className="text-body-sm font-bold" style={{ color: "var(--accent-error)" }}>
              Execution Error
            </p>
            <p className="text-caption mt-0.5" style={{ color: "var(--fg-secondary)" }}>{error}</p>
          </div>
          <button onClick={loadDetail} className="brutalist-btn brutalist-btn-secondary text-xs">
            Retry
          </button>
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* HUMAN APPROVAL REQUIRED GATE BANNER           */}
      {/* ══════════════════════════════════════════════ */}
      {detail?.status === "paused_approval" && (
        <div className="brutalist-card p-6 border-2 space-y-4"
             style={{ borderColor: "var(--accent-warning)", background: "rgba(245,158,11,0.05)" }}>
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-6 h-6 shrink-0" style={{ color: "var(--accent-warning)" }} />
            <div>
              <h3 className="text-h3 font-black uppercase text-[var(--accent-warning)]">
                HUMAN APPROVAL REQUIRED
              </h3>
              <p className="text-body-sm text-[var(--fg-secondary)]">
                Workflow paused at approval gate for agent:{" "}
                <span className="font-mono font-bold uppercase text-[var(--accent-secondary)]">
                  {detail.current_agent || "Orchestration Core"}
                </span>
                . Review agent context and decide whether to approve or reject.
              </p>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <textarea
              rows={2}
              placeholder="Add optional approval comments or instructions for downstream agents..."
              value={approvalComment}
              onChange={(e) => setApprovalComment(e.target.value)}
              className="w-full p-3 border-2 border-[var(--border-primary)] bg-[var(--bg-surface)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
            />
            <div className="flex items-center gap-3">
              <button
                onClick={handleApprove}
                disabled={actionLoading}
                className="brutalist-btn brutalist-btn-primary text-xs"
              >
                <Check className="w-4 h-4" />
                Approve Stage & Resume
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="brutalist-btn brutalist-btn-secondary text-xs text-[var(--accent-error)]"
              >
                <X className="w-4 h-4" />
                Reject Stage
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════ */}
      {/* DYNAMIC 5-AGENT EXECUTION GRAPH               */}
      {/* ══════════════════════════════════════════════ */}
      <div className="brutalist-card p-6" style={{ background: "var(--bg-surface)" }}>
        <h2 className="text-h4 mb-4" style={{ color: "var(--fg-primary)" }}>
          Orchestration Core & 5-Agent Execution Graph
        </h2>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 overflow-x-auto py-2">

          {/* Supervisor / Orchestration Core Node */}
          <div className="brutalist-card-sm p-3.5 text-center min-w-[130px]"
               style={{ borderColor: "var(--border-primary)", background: "var(--bg-secondary)" }}>
            <span className="text-[10px] font-bold text-[var(--fg-tertiary)] uppercase block">SYSTEM</span>
            <span className="text-xs font-extrabold uppercase block text-[var(--fg-primary)]">SUPERVISOR</span>
            <span className="text-[9px] font-mono text-[var(--accent-success)]">ACTIVE</span>
          </div>

          <span className="text-[var(--fg-tertiary)] font-bold">→</span>

          {/* 5 Agent Nodes */}
          {AGENTS_LIST.map((ag) => {
            const st = getAgentGraphStatus(ag.name);
            const isCurrent = detail?.current_agent === ag.name;

            return (
              <div key={ag.name} className="flex items-center gap-3">
                <div
                  className={`brutalist-card-sm p-3.5 text-center min-w-[120px] transition-transform ${isCurrent ? "scale-105" : ""}`}
                  style={{
                    borderColor: ag.color,
                    boxShadow: isCurrent ? `0 0 12px ${ag.color}` : "none",
                  }}
                >
                  <span className="text-[10px] font-mono font-bold block" style={{ color: ag.color }}>
                    {ag.number}
                  </span>
                  <span className="text-xs font-extrabold uppercase block text-[var(--fg-primary)]">
                    {ag.label}
                  </span>
                  <span
                    className="text-[9px] font-bold uppercase px-1.5 py-0.5 border inline-block mt-1"
                    style={{
                      color: getAgentStatusColor(st),
                      borderColor: getAgentStatusColor(st),
                    }}
                  >
                    {st.replace("_", " ")}
                  </span>
                </div>
                <span className="text-[var(--fg-tertiary)] font-bold">→</span>
              </div>
            );
          })}

          {/* Final Result Node */}
          <div className="brutalist-card-sm p-3.5 text-center min-w-[110px]"
               style={{
                 borderColor: detail?.status === "completed" ? "var(--accent-success)" : "var(--border-secondary)",
               }}>
            <span className="text-[10px] font-bold text-[var(--fg-tertiary)] uppercase block">RESULT</span>
            <span className="text-xs font-extrabold uppercase block text-[var(--fg-primary)]">OUTPUT</span>
            <span className="text-[9px] font-bold uppercase text-[var(--fg-tertiary)]">
              {detail?.status === "completed" ? "SUCCESS" : "PENDING"}
            </span>
          </div>

        </div>
      </div>

      {/* ══════════════════════════════════════════════ */}
      {/* SPLIT VIEW: EVENT STREAM + CHECKPOINT INSPECTOR*/}
      {/* ══════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* LEFT COLUMN — Real-Time Event Feed */}
        <div className="brutalist-card p-6 space-y-4" style={{ background: "var(--bg-surface)" }}>
          <div className="flex items-center justify-between border-b-2 border-[var(--border-primary)] pb-3">
            <h3 className="text-h3 font-black uppercase" style={{ color: "var(--fg-primary)" }}>
              Execution Events Stream
            </h3>
            {isStreaming && (
              <span className="text-caption font-bold text-[var(--accent-success)] flex items-center gap-1.5">
                <span className="status-dot status-dot-online" /> Streaming
              </span>
            )}
          </div>

          <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
            {eventStream.length === 0 ? (
              <p className="text-caption text-[var(--fg-tertiary)] py-8 text-center">
                No events streamed yet. Click &quot;Resume Stream&quot; or start workflow execution to observe SSE events.
              </p>
            ) : (
              eventStream.map((evt) => (
                <div
                  key={evt.id}
                  className="p-3 border-2 border-[var(--border-secondary)] bg-[var(--bg-primary)] space-y-1 animate-fade-in"
                >
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="font-bold text-[var(--accent-secondary)] uppercase">
                      [{evt.event}]
                    </span>
                    <span className="text-[var(--fg-tertiary)]">{evt.timestamp}</span>
                  </div>

                  {evt.agent && (
                    <span className="text-xs font-extrabold uppercase text-[var(--fg-primary)] block">
                      Agent: {evt.agent}
                    </span>
                  )}

                  {evt.toolName && (
                    <span className="text-caption font-mono text-[var(--accent-tertiary)] block">
                      Tool: {evt.toolName}
                    </span>
                  )}

                  {evt.output && (
                    <p className="text-caption font-mono text-[var(--fg-secondary)] line-clamp-3">
                      {evt.output}
                    </p>
                  )}

                  {evt.error && (
                    <p className="text-caption font-mono text-[var(--accent-error)]">
                      Error: {evt.error}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* RIGHT COLUMN — Data-Driven Checkpoint Inspector */}
        <div className="brutalist-card p-6 space-y-4" style={{ background: "var(--bg-surface)" }}>
          <div className="flex items-center justify-between border-b-2 border-[var(--border-primary)] pb-3">
            <h3 className="text-h3 font-black uppercase" style={{ color: "var(--fg-primary)" }}>
              Checkpoint & Shared State
            </h3>
            {activeCheckpoint && (
              <span className="text-caption font-mono text-[var(--fg-tertiary)]">
                Agent: {activeCheckpoint.agent_name}
              </span>
            )}
          </div>

          {/* Inspector Tabs */}
          <div className="flex border-b-2 border-[var(--border-primary)]">
            {[
              { id: "state", label: "Shared State" },
              { id: "tools", label: "Tool History" },
              { id: "research", label: "Research Context" },
              { id: "chat", label: "Chat Context" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  px-3 py-2 text-xs font-bold uppercase border-t-2 border-x-2 -mb-[2px] transition-colors
                  ${activeTab === tab.id
                    ? "border-[var(--border-primary)] bg-[var(--accent-primary)] text-[var(--fg-on-accent)]"
                    : "border-transparent text-[var(--fg-secondary)] hover:text-[var(--fg-primary)]"
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Inspector Data Content */}
          <div className="p-4 border-2 border-[var(--border-secondary)] bg-[var(--bg-secondary)] min-h-[360px] max-h-[420px] overflow-y-auto font-mono text-xs">
            {activeTab === "state" && (
              activeCheckpoint?.shared_state && Object.keys(activeCheckpoint.shared_state).length > 0 ? (
                <pre className="whitespace-pre-wrap text-[var(--fg-primary)]">
                  {JSON.stringify(activeCheckpoint.shared_state, null, 2)}
                </pre>
              ) : (
                <p className="text-caption text-[var(--fg-tertiary)] py-8 text-center font-sans">
                  No data available for this execution.
                </p>
              )
            )}

            {activeTab === "tools" && (
              activeCheckpoint?.tool_history && activeCheckpoint.tool_history.length > 0 ? (
                <pre className="whitespace-pre-wrap text-[var(--fg-primary)]">
                  {JSON.stringify(activeCheckpoint.tool_history, null, 2)}
                </pre>
              ) : (
                <p className="text-caption text-[var(--fg-tertiary)] py-8 text-center font-sans">
                  No data available for this execution.
                </p>
              )
            )}

            {activeTab === "research" && (
              activeCheckpoint?.research_context ? (
                <p className="whitespace-pre-wrap text-[var(--fg-primary)]">
                  {activeCheckpoint.research_context}
                </p>
              ) : (
                <p className="text-caption text-[var(--fg-tertiary)] py-8 text-center font-sans">
                  No data available for this execution.
                </p>
              )
            )}

            {activeTab === "chat" && (
              activeCheckpoint?.chat_context ? (
                <p className="whitespace-pre-wrap text-[var(--fg-primary)]">
                  {activeCheckpoint.chat_context}
                </p>
              ) : (
                <p className="text-caption text-[var(--fg-tertiary)] py-8 text-center font-sans">
                  No data available for this execution.
                </p>
              )
            )}
          </div>

          {/* Module Links */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              href="/app/artifacts"
              className="text-xs font-bold text-[var(--fg-secondary)] hover:text-[var(--accent-secondary)] underline underline-offset-4 flex items-center gap-1"
            >
              <Sparkles className="w-3.5 h-3.5" /> View Artifacts →
            </Link>
            <Link
              href="/app/workspace"
              className="text-xs font-bold text-[var(--fg-secondary)] hover:text-[var(--accent-secondary)] underline underline-offset-4 flex items-center gap-1"
            >
              <Folder className="w-3.5 h-3.5" /> View Workspace →
            </Link>
            <Link
              href="/app/agents"
              className="text-xs font-bold text-[var(--fg-secondary)] hover:text-[var(--accent-secondary)] underline underline-offset-4 flex items-center gap-1"
            >
              <Brain className="w-3.5 h-3.5" /> View 5 Agents →
            </Link>
          </div>

        </div>

      </div>

    </div>
  );
}

function getStatusColor(status: string) {
  switch (status.toLowerCase()) {
    case "completed":
      return "var(--accent-success)";
    case "running":
      return "var(--accent-tertiary)";
    case "paused_approval":
    case "paused":
      return "var(--accent-warning)";
    case "failed":
    case "cancelled":
      return "var(--accent-error)";
    default:
      return "var(--fg-tertiary)";
  }
}

function getAgentStatusColor(status: string) {
  switch (status) {
    case "COMPLETED":
      return "var(--accent-success)";
    case "RUNNING":
      return "var(--accent-tertiary)";
    case "PAUSED_APPROVAL":
      return "var(--accent-warning)";
    case "FAILED":
      return "var(--accent-error)";
    default:
      return "var(--fg-tertiary)";
  }
}
