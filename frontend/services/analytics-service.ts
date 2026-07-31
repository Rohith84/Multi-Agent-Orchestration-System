/**
 * Analytics and Prompt Registry Service — API calls for LLMOps, metrics, and prompt versioning.
 */

import api from "@/lib/api";

export interface ModelPerformanceStats {
  model_name: string;
  total_calls: number;
  avg_duration: number;
  avg_tokens: number;
  avg_score: number;
  success_rate: number;
}

export interface ToolPerformanceStats {
  tool_name: string;
  category: string;
  total_calls: number;
  avg_duration: number;
  success_rate: number;
  failure_count: number;
}

export interface RAGPerformanceStats {
  total_queries: number;
  avg_retrieval_latency: number;
  avg_similarity_score: number;
  total_chunks_retrieved: number;
}

export interface AgentMetric {
  id: string;
  workflow_id: string;
  agent_name: string;
  model: string;
  start_time: string;
  end_time: string;
  duration: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  status: string;
  retry_count: number;
  tool_calls: number;
  knowledge_chunks: number;
  score: number;
  eval_breakdown: Record<string, unknown>;
  created_at: string;
}

export interface DashboardAnalyticsResponse {
  overall_quality_score: number;
  total_workflows_executed: number;
  total_tokens_consumed: number;
  avg_workflow_latency: number;
  success_rate_percentage: number;
  model_stats: ModelPerformanceStats[];
  tool_stats: ToolPerformanceStats[];
  rag_stats: RAGPerformanceStats;
  recent_agent_metrics: AgentMetric[];
}

export interface PromptVersion {
  id: string;
  agent_name: string;
  version: string;
  template: string;
  description: string;
  active: boolean;
  created_at: string;
}

export interface PromptCreateRequest {
  agent_name: string;
  version: string;
  template: string;
  description?: string;
}

/**
 * Fetch analytics dashboard metrics.
 * GET /api/analytics/dashboard
 */
export async function fetchDashboardAnalytics(): Promise<DashboardAnalyticsResponse> {
  const { data } = await api.get<DashboardAnalyticsResponse>("/api/analytics/dashboard");
  return data;
}

/**
 * Download analytics report in JSON or CSV format.
 * GET /api/analytics/export
 */
export async function exportAnalyticsReport(format: "json" | "csv" = "json"): Promise<string> {
  const { data } = await api.get<string>("/api/analytics/export", {
    params: { format },
    responseType: "text",
  });
  return data;
}

/**
 * List all prompt versions in Prompt Registry.
 * GET /api/prompts
 */
export async function fetchPromptVersions(): Promise<PromptVersion[]> {
  const { data } = await api.get<PromptVersion[]>("/api/prompts");
  return data;
}

/**
 * Create a new prompt version.
 * POST /api/prompts
 */
export async function createPromptVersion(request: PromptCreateRequest): Promise<PromptVersion> {
  const { data } = await api.post<PromptVersion>("/api/prompts", request);
  return data;
}

/**
 * Activate a prompt version.
 * POST /api/prompts/{id}/activate
 */
export async function activatePromptVersion(promptId: string): Promise<PromptVersion> {
  const { data } = await api.post<PromptVersion>(`/api/prompts/${promptId}/activate`);
  return data;
}
