/**
 * Workflows Page — Human-in-the-Loop Workflow Management & Checkpoints Center.
 *
 * Features:
 * - List all workflows with status badges and live progress bars
 * - Inspect workflow execution timeline, checkpoints, and shared states
 * - Approve/Reject pending approval gate requests with comment input
 * - Resume, Restart, or Cancel workflow executions
 * - Schedule recurring or delayed workflows
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Play,
  Pause,
  RotateCcw,
  XCircle,
  CheckCircle2,
  Clock,
  Calendar,
  Layers,
  ChevronRight,
  Loader2,
  RefreshCw,
  Plus,
  ShieldAlert,
  Sliders,
  Check,
  X,
  FileCode,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchWorkflows,
  fetchWorkflowDetail,
  approveWorkflowStage,
  rejectWorkflowStage,
  cancelWorkflow,
  restartWorkflow,
  createWorkflowSchedule,
  fetchWorkflowSchedules,
  type Workflow,
  type WorkflowDetail,
  type WorkflowSchedule,
} from "@/services/workflows-service";

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [schedules, setSchedules] = useState<WorkflowSchedule[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [commentInput, setCommentInput] = useState("");
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [schedTitle, setSchedTitle] = useState("");
  const [schedMessage, setSchedMessage] = useState("");
  const [schedCron, setSchedCron] = useState("0 0 * * *");
  const [schedApprovalAgents, setSchedApprovalAgents] = useState<string[]>(["coder"]);

  const loadData = useCallback(async () => {
    try {
      const [wfRes, schedRes] = await Promise.all([
        fetchWorkflows(),
        fetchWorkflowSchedules(),
      ]);
      setWorkflows(wfRes.workflows);
      setSchedules(schedRes.schedules);
      if (wfRes.workflows.length > 0 && !selectedWorkflow) {
        const detail = await fetchWorkflowDetail(wfRes.workflows[0].id);
        setSelectedWorkflow(detail);
      }
    } catch (err) {
      console.error("Failed to load workflow data:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedWorkflow]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const selectWorkflowItem = async (id: string) => {
    try {
      const detail = await fetchWorkflowDetail(id);
      setSelectedWorkflow(detail);
      setCommentInput("");
    } catch (err) {
      console.error("Failed to fetch workflow detail:", err);
    }
  };

  const handleApprove = async () => {
    if (!selectedWorkflow) return;
    setActionLoading(true);
    try {
      await approveWorkflowStage(selectedWorkflow.id, commentInput);
      await loadData();
      const updated = await fetchWorkflowDetail(selectedWorkflow.id);
      setSelectedWorkflow(updated);
    } catch (err) {
      console.error("Failed to approve workflow stage:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedWorkflow) return;
    setActionLoading(true);
    try {
      const updated = await rejectWorkflowStage(selectedWorkflow.id, commentInput);
      setSelectedWorkflow(updated);
      await loadData();
    } catch (err) {
      console.error("Failed to reject workflow stage:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!selectedWorkflow) return;
    setActionLoading(true);
    try {
      const updated = await cancelWorkflow(selectedWorkflow.id);
      setSelectedWorkflow(updated);
      await loadData();
    } catch (err) {
      console.error("Failed to cancel workflow:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestart = async () => {
    if (!selectedWorkflow) return;
    setActionLoading(true);
    try {
      const updated = await restartWorkflow(selectedWorkflow.id);
      setSelectedWorkflow(updated);
      await loadData();
    } catch (err) {
      console.error("Failed to restart workflow:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateSchedule = async () => {
    if (!schedTitle || !schedMessage) return;
    setActionLoading(true);
    try {
      await createWorkflowSchedule({
        title: schedTitle,
        message: schedMessage,
        cron_expression: schedCron,
        require_approval_agents: schedApprovalAgents,
      });
      setShowScheduleModal(false);
      setSchedTitle("");
      setSchedMessage("");
      await loadData();
    } catch (err) {
      console.error("Failed to create schedule:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Running
          </span>
        );
      case "paused_approval":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <ShieldAlert className="h-3.5 w-3.5" /> Waiting Approval
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3.5 w-3.5" /> Completed
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-red-500/10 text-red-400 border border-red-500/20">
            <XCircle className="h-3.5 w-3.5" /> Failed
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-zinc-700/50 text-zinc-400 border border-zinc-600/30">
            <X className="h-3.5 w-3.5" /> Cancelled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-zinc-800 text-zinc-400">
            Pending
          </span>
        );
    }
  };

  return (
    <main className="flex-1 p-6 sm:p-8 lg:p-12 max-w-7xl mx-auto w-full">
      {/* Page Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors mb-3"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Layers className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Workflows & HITL Center</h1>
              <p className="text-sm text-zinc-400">
                Checkpoints • Human Approvals • Planning Memory • Scheduling
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={() => loadData()}
            variant="outline"
            size="sm"
            className="border-zinc-700/50 text-zinc-300 hover:bg-zinc-800"
          >
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh
          </Button>
          <Button
            onClick={() => setShowScheduleModal(true)}
            size="sm"
            className="bg-gradient-to-r from-indigo-600 to-violet-500 text-white font-medium shadow-md shadow-indigo-500/20"
          >
            <Plus className="h-4 w-4 mr-2" /> Schedule Workflow
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Workflows List Column */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
              Workflows ({workflows.length})
            </h2>

            {workflows.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-8 text-center backdrop-blur-sm">
                <Layers className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                <p className="text-sm text-zinc-500">No workflows executed yet.</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[700px] overflow-y-auto pr-1">
                {workflows.map((wf) => {
                  const isSelected = selectedWorkflow?.id === wf.id;
                  return (
                    <div
                      key={wf.id}
                      onClick={() => selectWorkflowItem(wf.id)}
                      className={`group relative overflow-hidden rounded-xl border p-4 backdrop-blur-sm cursor-pointer transition-all duration-300 ${
                        isSelected
                          ? "bg-zinc-800/80 border-indigo-500/40 ring-1 ring-indigo-500/30"
                          : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="text-sm font-semibold text-white line-clamp-1">
                          {wf.title}
                        </h3>
                        <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-white transition-colors" />
                      </div>

                      <p className="text-xs text-zinc-400 line-clamp-2 mb-3">
                        {wf.user_request}
                      </p>

                      {/* Progress Bar */}
                      <div className="mb-3">
                        <div className="flex justify-between text-[10px] text-zinc-500 mb-1">
                          <span>Stage: {wf.current_agent}</span>
                          <span>{wf.progress_percentage}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-violet-400 transition-all duration-500"
                            style={{ width: `${wf.progress_percentage}%` }}
                          />
                        </div>
                      </div>

                      <div className="flex items-center justify-between">
                        {getStatusBadge(wf.status)}
                        <span className="text-[10px] text-zinc-500">
                          {new Date(wf.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Workflow Detail & Checkpoints Column */}
          <div className="lg:col-span-2 space-y-6">
            {selectedWorkflow ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-sm space-y-6">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h2 className="text-lg font-bold text-white">{selectedWorkflow.title}</h2>
                      {getStatusBadge(selectedWorkflow.status)}
                    </div>
                    <p className="text-xs text-zinc-400 font-mono">ID: {selectedWorkflow.id}</p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={handleRestart}
                      disabled={actionLoading}
                      variant="outline"
                      size="sm"
                      className="border-zinc-700/50 text-zinc-300 hover:bg-zinc-800"
                    >
                      <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Restart
                    </Button>

                    {["running", "paused_approval"].includes(selectedWorkflow.status) && (
                      <Button
                        onClick={handleCancel}
                        disabled={actionLoading}
                        variant="outline"
                        size="sm"
                        className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                      >
                        <X className="h-3.5 w-3.5 mr-1.5" /> Cancel
                      </Button>
                    )}
                  </div>
                </div>

                {/* HITL Approval Request Banner */}
                {selectedWorkflow.status === "paused_approval" && (
                  <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 backdrop-blur-sm animate-pulse">
                    <div className="flex items-start gap-3 mb-3">
                      <ShieldAlert className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <h3 className="text-sm font-semibold text-amber-300">
                          Human Approval Required: Stage '{selectedWorkflow.current_agent.toUpperCase()}'
                        </h3>
                        <p className="text-xs text-amber-300/80 mt-1">
                          This workflow is configured with an approval gate before executing the {selectedWorkflow.current_agent} agent.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-3 mt-4">
                      <input
                        type="text"
                        value={commentInput}
                        onChange={(e) => setCommentInput(e.target.value)}
                        placeholder="Optional approval/rejection notes..."
                        className="w-full bg-zinc-950/80 border border-amber-500/30 rounded-lg px-3 py-2 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-amber-400"
                      />

                      <div className="flex gap-3">
                        <Button
                          onClick={handleApprove}
                          disabled={actionLoading}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex-1"
                        >
                          <Check className="h-4 w-4 mr-1.5" /> Approve & Resume
                        </Button>
                        <Button
                          onClick={handleReject}
                          disabled={actionLoading}
                          className="bg-red-600 hover:bg-red-500 text-white font-medium text-xs flex-1"
                        >
                          <X className="h-4 w-4 mr-1.5" /> Reject Workflow
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Shared User Request */}
                <div>
                  <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                    User Request
                  </h3>
                  <div className="rounded-lg bg-zinc-950/60 p-3 border border-zinc-800 text-xs text-zinc-300 font-mono leading-relaxed">
                    {selectedWorkflow.user_request}
                  </div>
                </div>

                {/* State Checkpoints Timeline */}
                <div>
                  <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
                    Checkpoints & Execution Stages ({selectedWorkflow.checkpoints.length})
                  </h3>

                  {selectedWorkflow.checkpoints.length === 0 ? (
                    <p className="text-xs text-zinc-500 italic">No checkpoints recorded yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {selectedWorkflow.checkpoints.map((cp, idx) => (
                        <div
                          key={cp.id}
                          className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4 space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="h-6 w-6 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-[10px] font-bold text-indigo-400">
                                {idx + 1}
                              </span>
                              <span className="text-xs font-semibold text-white capitalize">
                                {cp.agent_name} Agent Checkpoint
                              </span>
                            </div>
                            <span className="text-[10px] text-zinc-500">
                              {new Date(cp.created_at).toLocaleTimeString()}
                            </span>
                          </div>

                          <div className="text-[11px] text-zinc-400 font-mono bg-zinc-900/80 p-2.5 rounded border border-zinc-800/80 max-h-32 overflow-y-auto">
                            <div className="text-indigo-300 font-semibold mb-1">State Snapshot:</div>
                            {JSON.stringify(cp.shared_state, null, 2).slice(0, 300)}...
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Approval History */}
                {selectedWorkflow.approvals.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                      Approval History
                    </h3>
                    <div className="space-y-2">
                      {selectedWorkflow.approvals.map((app) => (
                        <div
                          key={app.id}
                          className="flex items-center justify-between p-3 rounded-lg bg-zinc-950/40 border border-zinc-800 text-xs"
                        >
                          <span className="font-semibold text-zinc-300 capitalize">
                            {app.agent_name} Stage
                          </span>
                          <div className="flex items-center gap-3">
                            {app.comments && (
                              <span className="text-zinc-500 italic font-mono text-[10px]">
                                "{app.comments}"
                              </span>
                            )}
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                app.status === "approved"
                                  ? "bg-emerald-500/20 text-emerald-400"
                                  : app.status === "rejected"
                                  ? "bg-red-500/20 text-red-400"
                                  : "bg-amber-500/20 text-amber-400"
                              }`}
                            >
                              {app.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-12 text-center backdrop-blur-sm">
                <Layers className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                <p className="text-sm text-zinc-500">Select a workflow to view state checkpoints.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Schedule Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Calendar className="h-5 w-5 text-indigo-400" /> Schedule Workflow
            </h3>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-zinc-400 mb-1 block">Title</label>
                <input
                  type="text"
                  value={schedTitle}
                  onChange={(e) => setSchedTitle(e.target.value)}
                  placeholder="e.g. Daily Security Audit Workflow"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-400 mb-1 block">Prompt / Request</label>
                <textarea
                  value={schedMessage}
                  onChange={(e) => setSchedMessage(e.target.value)}
                  placeholder="What should the agents do?"
                  rows={3}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-400 mb-1 block">Cron Expression</label>
                <input
                  type="text"
                  value={schedCron}
                  onChange={(e) => setSchedCron(e.target.value)}
                  placeholder="0 0 * * *"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white font-mono"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button
                onClick={() => setShowScheduleModal(false)}
                variant="outline"
                size="sm"
                className="border-zinc-800 text-zinc-400"
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreateSchedule}
                disabled={actionLoading}
                size="sm"
                className="bg-indigo-600 text-white"
              >
                Save Schedule
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
