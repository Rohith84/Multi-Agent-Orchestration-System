/**
 * /app/workflows — Enterprise Workflow Management Center.
 *
 * Provides:
 * - Real workflow list fetched from GET /api/workflows
 * - Search by workflow title or request text
 * - Filter by status (ALL, RUNNING, PAUSED_APPROVAL, COMPLETED, FAILED, CANCELLED)
 * - Enterprise table with duration, current agent, progress/state, updated date
 * - Action buttons: Open Detail (/app/workflows/[id]), Resume, Restart, Cancel
 * - Create & Schedule Workflow modals
 * - Skeleton loading states, error retry state, and neo-brutalist empty state
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type {
  Workflow,
  WorkflowDetail,
  WorkflowSchedule,
} from "@/services/workflows-service";
import {
  fetchWorkflows,
  createWorkflowSchedule,
  cancelWorkflow,
  restartWorkflow,
  resumeWorkflow,
} from "@/services/workflows-service";
import {
  Workflow as WorkflowIcon,
  Search,
  Plus,
  RefreshCw,
  AlertTriangle,
  Play,
  Pause,
  RotateCcw,
  XCircle,
  Clock,
  Calendar,
  ChevronRight,
  ArrowRight,
  Zap,
  Sliders,
  Filter,
  CheckCircle2,
} from "lucide-react";

export default function WorkflowManagementPage() {
  const router = useRouter();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [totalWorkflows, setTotalWorkflows] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  // Create Modal & Schedule Modal State
  const [showRunModal, setShowRunModal] = useState(false);
  const [runGoalInput, setRunGoalInput] = useState("");
  const [requireApprovalAgents, setRequireApprovalAgents] = useState<string[]>(["coder"]);
  const [submittingRun, setSubmittingRun] = useState(false);

  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [schedTitle, setSchedTitle] = useState("");
  const [schedMessage, setSchedMessage] = useState("");
  const [schedCron, setSchedCron] = useState("0 9 * * 1-5");
  const [submittingSched, setSubmittingSched] = useState(false);

  const loadData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    setError(null);

    try {
      const res = await fetchWorkflows({ limit: 100, offset: 0 });
      setWorkflows(res.workflows || []);
      setTotalWorkflows(res.total || 0);
    } catch (err: any) {
      console.error("Failed to fetch workflows:", err);
      setError(err?.message || "Failed to load workflows from backend.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter workflows
  const filteredWorkflows = workflows.filter((wf) => {
    const matchesSearch =
      wf.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      wf.user_request.toLowerCase().includes(searchQuery.toLowerCase()) ||
      wf.id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === "ALL" || wf.status.toUpperCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // Handle Actions
  const handleCancel = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await cancelWorkflow(id);
      loadData(true);
    } catch (err) {
      console.error("Failed to cancel workflow:", err);
    }
  };

  const handleRestart = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await restartWorkflow(id);
      loadData(true);
    } catch (err) {
      console.error("Failed to restart workflow:", err);
    }
  };

  const handleResume = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await resumeWorkflow(id);
      router.push(`/app/workflows/${id}`);
    } catch (err) {
      console.error("Failed to resume workflow:", err);
    }
  };

  // Submit Run Workflow Modal
  const handleStartWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!runGoalInput.trim() || submittingRun) return;
    setSubmittingRun(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${API_URL}/api/workflows/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: runGoalInput.trim(),
          require_approval_agents: requireApprovalAgents,
        }),
      });

      if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

      // Read stream until workflow_id is found
      const reader = response.body?.getReader();
      if (reader) {
        let foundId = "";
        for (let i = 0; i < 10; i++) {
          const { value, done } = await reader.read();
          if (done) break;
          const text = new TextDecoder().decode(value);
          const match = text.match(/"workflow_id":\s*"([^"]+)"/);
          if (match && match[1]) {
            foundId = match[1];
            break;
          }
        }
        if (foundId) {
          setShowRunModal(false);
          setRunGoalInput("");
          router.push(`/app/workflows/${foundId}`);
          return;
        }
      }

      // Fallback: fetch latest workflow list and navigate
      const latest = await fetchWorkflows({ limit: 1 });
      if (latest.workflows && latest.workflows.length > 0) {
        setShowRunModal(false);
        setRunGoalInput("");
        router.push(`/app/workflows/${latest.workflows[0].id}`);
        return;
      }

      setShowRunModal(false);
      setRunGoalInput("");
      loadData(true);
    } catch (err: any) {
      console.error("Failed to start workflow:", err);
      alert(`Error: ${err?.message || "Failed to start workflow"}`);
    } finally {
      setSubmittingRun(false);
    }
  };

  // Submit Schedule Modal
  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!schedTitle.trim() || !schedMessage.trim() || submittingSched) return;
    setSubmittingSched(true);

    try {
      await createWorkflowSchedule({
        title: schedTitle.trim(),
        message: schedMessage.trim(),
        cron_expression: schedCron.trim(),
      });
      setShowScheduleModal(false);
      setSchedTitle("");
      setSchedMessage("");
      loadData(true);
      alert("Workflow schedule created successfully!");
    } catch (err: any) {
      console.error("Failed to create schedule:", err);
      alert(`Error: ${err?.message || "Failed to create schedule"}`);
    } finally {
      setSubmittingSched(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">

      {/* Header Banner */}
      <div className="p-6 brutalist-card flex flex-col md:flex-row md:items-center justify-between gap-4"
           style={{ background: "var(--bg-surface)" }}>
        <div>
          <div className="inline-block mb-2">
            <span className="brutalist-btn-primary text-caption px-2.5 py-0.5 border"
                  style={{ borderColor: "var(--border-primary)" }}>
              AUTOMATION ENGINE
            </span>
          </div>
          <h1 className="text-h1 font-black tracking-tight" style={{ color: "var(--fg-primary)" }}>
            Workflows
          </h1>
          <p className="text-body-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
            Manage, execute and monitor multi-agent workflows.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="brutalist-btn brutalist-btn-secondary text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowScheduleModal(true)}
            className="brutalist-btn brutalist-btn-secondary text-xs"
          >
            <Calendar className="w-3.5 h-3.5" />
            Schedule
          </button>
          <button
            onClick={() => setShowRunModal(true)}
            className="brutalist-btn brutalist-btn-primary text-xs"
          >
            <Zap className="w-3.5 h-3.5" />
            Run Workflow
          </button>
        </div>
      </div>

      {/* Search & Status Filters */}
      <div className="p-4 brutalist-card-sm flex flex-col sm:flex-row items-center justify-between gap-4"
           style={{ background: "var(--bg-surface)" }}>
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-[var(--fg-tertiary)]" />
          <input
            type="text"
            placeholder="Search workflows by title, request, or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border-2 border-[var(--border-secondary)] bg-[var(--bg-primary)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none focus:border-[var(--border-primary)]"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-3.5 h-3.5 text-[var(--fg-tertiary)]" />
          <span className="text-xs font-bold uppercase text-[var(--fg-secondary)]">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border-2 border-[var(--border-secondary)] bg-[var(--bg-primary)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
          >
            <option value="ALL">ALL STATUSES ({workflows.length})</option>
            <option value="RUNNING">RUNNING</option>
            <option value="PAUSED_APPROVAL">PAUSED APPROVAL</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 border-2 flex items-center gap-3"
             style={{ borderColor: "var(--accent-error)", background: "rgba(239,68,68,0.05)" }}>
          <AlertTriangle className="w-5 h-5 shrink-0" style={{ color: "var(--accent-error)" }} />
          <div className="flex-1">
            <p className="text-body-sm font-bold" style={{ color: "var(--accent-error)" }}>
              Unable to load workflows
            </p>
            <p className="text-caption mt-0.5" style={{ color: "var(--fg-secondary)" }}>
              {error}
            </p>
          </div>
          <button onClick={() => loadData()} className="brutalist-btn brutalist-btn-secondary text-xs">
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeletons */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-16 border-2 border-[var(--border-secondary)] bg-[var(--bg-surface)] animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredWorkflows.length === 0 && (
        <div className="p-12 brutalist-card text-center space-y-4" style={{ background: "var(--bg-surface)" }}>
          <div className="w-12 h-12 border-2 border-[var(--border-primary)] bg-[var(--bg-secondary)] flex items-center justify-center mx-auto">
            <WorkflowIcon className="w-6 h-6 text-[var(--fg-secondary)]" />
          </div>
          <div>
            <h3 className="text-h3 font-black uppercase" style={{ color: "var(--fg-primary)" }}>
              NO WORKFLOWS FOUND
            </h3>
            <p className="text-body-sm max-w-md mx-auto mt-1" style={{ color: "var(--fg-secondary)" }}>
              {searchQuery || statusFilter !== "ALL"
                ? "No workflows match your active filter criteria."
                : "Create your first multi-agent workflow to begin orchestrating real work."
              }
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button onClick={() => setShowRunModal(true)} className="brutalist-btn brutalist-btn-primary text-xs">
              <Zap className="w-3.5 h-3.5" />
              Create Workflow
            </button>
            <Link href="/app/workflow-builder" className="brutalist-btn brutalist-btn-secondary text-xs">
              Open Builder
            </Link>
          </div>
        </div>
      )}

      {/* Workflow Enterprise Table */}
      {!loading && !error && filteredWorkflows.length > 0 && (
        <div className="brutalist-card overflow-hidden" style={{ background: "var(--bg-surface)" }}>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b-2 border-[var(--border-primary)] bg-[var(--bg-secondary)] text-[10px] font-extrabold uppercase tracking-wider text-[var(--fg-tertiary)]">
                  <th className="py-3 px-4">WORKFLOW</th>
                  <th className="py-3 px-4">STATUS</th>
                  <th className="py-3 px-4">CURRENT AGENT</th>
                  <th className="py-3 px-4">PROGRESS / DURATION</th>
                  <th className="py-3 px-4">UPDATED</th>
                  <th className="py-3 px-4 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-secondary)] text-xs font-bold">
                {filteredWorkflows.map((wf) => {
                  const statusColor = getStatusColor(wf.status);
                  return (
                    <tr
                      key={wf.id}
                      onClick={() => router.push(`/app/workflows/${wf.id}`)}
                      className="hover:bg-[var(--bg-secondary)] cursor-pointer transition-colors"
                    >
                      {/* Title & Request */}
                      <td className="py-3.5 px-4">
                        <div className="max-w-md">
                          <span className="font-extrabold block truncate text-[var(--fg-primary)]">
                            {wf.title || "Untitled Workflow"}
                          </span>
                          <span className="text-[10px] font-mono text-[var(--fg-tertiary)] block truncate">
                            ID: {wf.id.substring(0, 8)}... | Request: {wf.user_request}
                          </span>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4">
                        <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 border"
                              style={{ color: statusColor, borderColor: statusColor }}>
                          {wf.status.replace("_", " ")}
                        </span>
                      </td>

                      {/* Current Agent */}
                      <td className="py-3.5 px-4 font-mono text-xs text-[var(--fg-primary)]">
                        {wf.current_agent ? (
                          <span className="uppercase text-[var(--accent-secondary)]">
                            {wf.current_agent}
                          </span>
                        ) : (
                          <span className="text-[var(--fg-tertiary)]">—</span>
                        )}
                      </td>

                      {/* Progress / Duration */}
                      <td className="py-3.5 px-4">
                        <div className="space-y-1">
                          <span className="text-caption font-mono text-[var(--fg-secondary)] block">
                            {wf.execution_time ? `${wf.execution_time.toFixed(1)}s` : "--"}
                          </span>
                          {wf.progress_percentage !== undefined && wf.progress_percentage !== null ? (
                            <div className="w-24 h-1.5 bg-[var(--bg-secondary)] overflow-hidden">
                              <div
                                className="h-full bg-[var(--accent-primary)] transition-all"
                                style={{ width: `${wf.progress_percentage}%` }}
                              />
                            </div>
                          ) : null}
                        </div>
                      </td>

                      {/* Updated */}
                      <td className="py-3.5 px-4 text-caption font-mono text-[var(--fg-tertiary)]">
                        {new Date(wf.updated_at || wf.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                          {wf.status === "paused_approval" && (
                            <button
                              onClick={(e) => handleResume(wf.id, e)}
                              className="px-2 py-1 text-[10px] font-bold border border-[var(--accent-success)] text-[var(--accent-success)] hover:bg-[var(--accent-success)] hover:text-black transition-colors"
                            >
                              Approve / Resume
                            </button>
                          )}
                          {wf.status === "running" && (
                            <button
                              onClick={(e) => handleCancel(wf.id, e)}
                              className="px-2 py-1 text-[10px] font-bold border border-[var(--accent-error)] text-[var(--accent-error)] hover:bg-[var(--accent-error)] hover:text-white transition-colors"
                            >
                              Cancel
                            </button>
                          )}
                          {(wf.status === "failed" || wf.status === "completed") && (
                            <button
                              onClick={(e) => handleRestart(wf.id, e)}
                              className="px-2 py-1 text-[10px] font-bold border border-[var(--border-secondary)] text-[var(--fg-secondary)] hover:text-[var(--fg-primary)] transition-colors"
                            >
                              Restart
                            </button>
                          )}
                          <Link
                            href={`/app/workflows/${wf.id}`}
                            className="px-2.5 py-1 text-[10px] font-bold border-2 border-[var(--border-primary)] bg-[var(--bg-surface)] hover:bg-[var(--accent-primary)] hover:text-[var(--fg-on-accent)] transition-colors"
                          >
                            Open →
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: Run Workflow */}
      {showRunModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="brutalist-card p-6 w-full max-w-lg space-y-4" style={{ background: "var(--bg-surface)" }}>
            <h3 className="text-h3 font-black uppercase" style={{ color: "var(--fg-primary)" }}>
              Run Multi-Agent Workflow
            </h3>
            <p className="text-body-sm" style={{ color: "var(--fg-secondary)" }}>
              Enter a task description or objective. The Orchestration Core will dispatch the 5 execution agents to plan, research, code, test, and review.
            </p>
            <form onSubmit={handleStartWorkflow} className="space-y-4">
              <textarea
                rows={3}
                required
                placeholder="e.g. Build a REST API endpoint for user authentication with unit tests..."
                value={runGoalInput}
                onChange={(e) => setRunGoalInput(e.target.value)}
                className="w-full p-3 border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
              />

              <div>
                <label className="text-caption font-bold uppercase block mb-1.5" style={{ color: "var(--fg-secondary)" }}>
                  Require Human Approval Gates
                </label>
                <div className="flex flex-wrap gap-4 p-2.5 border-2 border-[var(--border-primary)] bg-[var(--bg-primary)]">
                  {["coder", "tester", "reviewer"].map((agent) => (
                    <label key={agent} className="flex items-center gap-2 text-xs font-bold uppercase cursor-pointer" style={{ color: "var(--fg-primary)" }}>
                      <input
                        type="checkbox"
                        checked={requireApprovalAgents.includes(agent)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setRequireApprovalAgents((prev) => [...prev, agent]);
                          } else {
                            setRequireApprovalAgents((prev) => prev.filter((a) => a !== agent));
                          }
                        }}
                        className="w-4 h-4 accent-[var(--accent-lime)]"
                      />
                      {agent}
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRunModal(false)}
                  className="brutalist-btn brutalist-btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingRun}
                  className="brutalist-btn brutalist-btn-primary text-xs"
                >
                  {submittingRun ? "Launching Stream..." : "Execute Workflow"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Schedule Workflow */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="brutalist-card p-6 w-full max-w-lg space-y-4" style={{ background: "var(--bg-surface)" }}>
            <h3 className="text-h3 font-black uppercase" style={{ color: "var(--fg-primary)" }}>
              Schedule Workflow Execution
            </h3>
            <form onSubmit={handleCreateSchedule} className="space-y-4">
              <div>
                <label className="text-caption font-bold uppercase block mb-1" style={{ color: "var(--fg-secondary)" }}>
                  Schedule Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="Daily Security Audit"
                  value={schedTitle}
                  onChange={(e) => setSchedTitle(e.target.value)}
                  className="w-full p-2.5 border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-caption font-bold uppercase block mb-1" style={{ color: "var(--fg-secondary)" }}>
                  Task Request Message
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Run security vulnerability scan on workspace codebase..."
                  value={schedMessage}
                  onChange={(e) => setSchedMessage(e.target.value)}
                  className="w-full p-2.5 border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-caption font-bold uppercase block mb-1" style={{ color: "var(--fg-secondary)" }}>
                  Cron Expression (5-field)
                </label>
                <input
                  type="text"
                  required
                  placeholder="0 9 * * 1-5"
                  value={schedCron}
                  onChange={(e) => setSchedCron(e.target.value)}
                  className="w-full p-2.5 border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] font-mono text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className="brutalist-btn brutalist-btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingSched}
                  className="brutalist-btn brutalist-btn-primary text-xs"
                >
                  {submittingSched ? "Saving Schedule..." : "Save Schedule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
