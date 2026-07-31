/**
 * Workflows service — API client for workflow management, approvals, checkpoints, and scheduling.
 */

import api from "@/lib/api";

export interface WorkflowCheckpoint {
  id: string;
  workflow_id: string;
  agent_name: string;
  shared_state: Record<string, unknown>;
  tool_history: Array<Record<string, unknown>>;
  research_context: string;
  chat_context: string;
  created_at: string;
}

export interface WorkflowApproval {
  id: string;
  workflow_id: string;
  agent_name: string;
  status: "pending" | "approved" | "rejected";
  comments: string | null;
  requested_at: string;
  decided_at: string | null;
}

export interface Workflow {
  id: string;
  session_id: string;
  title: string;
  user_request: string;
  status: "pending" | "running" | "paused_approval" | "completed" | "failed" | "cancelled";
  current_agent: string;
  progress_percentage: number;
  require_approval_agents: string[];
  execution_time: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  checkpoints: WorkflowCheckpoint[];
  approvals: WorkflowApproval[];
}

export interface WorkflowListResponse {
  workflows: Workflow[];
  total: number;
}

export interface WorkflowSchedule {
  id: string;
  title: string;
  user_request: string;
  cron_expression: string;
  require_approval_agents: string[];
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface WorkflowScheduleListResponse {
  schedules: WorkflowSchedule[];
  total: number;
}

export interface WorkflowScheduleRequest {
  title: string;
  message: string;
  cron_expression?: string;
  require_approval_agents?: string[];
}

/**
 * Fetch all workflows.
 * GET /api/workflows
 */
export async function fetchWorkflows(params?: {
  limit?: number;
  offset?: number;
}): Promise<WorkflowListResponse> {
  const { data } = await api.get<WorkflowListResponse>("/api/workflows", {
    params,
  });
  return data;
}

/**
 * Fetch detailed state of a workflow.
 * GET /api/workflows/{id}
 */
export async function fetchWorkflowDetail(
  workflowId: string
): Promise<WorkflowDetail> {
  const { data } = await api.get<WorkflowDetail>(`/api/workflows/${workflowId}`);
  return data;
}

/**
 * Approve a pending workflow stage.
 * POST /api/workflows/{id}/approve
 */
export async function approveWorkflowStage(
  workflowId: string,
  comments?: string
): Promise<WorkflowDetail> {
  const { data } = await api.post<WorkflowDetail>(
    `/api/workflows/${workflowId}/approve`,
    { comments }
  );
  return data;
}

/**
 * Reject a pending workflow stage.
 * POST /api/workflows/{id}/reject
 */
export async function rejectWorkflowStage(
  workflowId: string,
  comments?: string
): Promise<WorkflowDetail> {
  const { data } = await api.post<WorkflowDetail>(
    `/api/workflows/${workflowId}/reject`,
    { comments }
  );
  return data;
}

/**
 * Resume a paused/failed workflow.
 * POST /api/workflows/{id}/resume
 */
export async function resumeWorkflow(
  workflowId: string
): Promise<void> {
  await api.post(`/api/workflows/${workflowId}/resume`);
}

/**
 * Cancel a workflow.
 * POST /api/workflows/{id}/cancel
 */
export async function cancelWorkflow(
  workflowId: string
): Promise<WorkflowDetail> {
  const { data } = await api.post<WorkflowDetail>(
    `/api/workflows/${workflowId}/cancel`
  );
  return data;
}

/**
 * Restart a workflow from START.
 * POST /api/workflows/{id}/restart
 */
export async function restartWorkflow(
  workflowId: string
): Promise<WorkflowDetail> {
  const { data } = await api.post<WorkflowDetail>(
    `/api/workflows/${workflowId}/restart`
  );
  return data;
}

/**
 * Create a workflow schedule.
 * POST /api/workflows/schedule
 */
export async function createWorkflowSchedule(
  request: WorkflowScheduleRequest
): Promise<WorkflowSchedule> {
  const { data } = await api.post<WorkflowSchedule>(
    "/api/workflows/schedule",
    request
  );
  return data;
}

/**
 * Fetch all workflow schedules.
 * GET /api/workflows/schedules
 */
export async function fetchWorkflowSchedules(): Promise<WorkflowScheduleListResponse> {
  const { data } = await api.get<WorkflowScheduleListResponse>(
    "/api/workflows/schedules"
  );
  return data;
}
