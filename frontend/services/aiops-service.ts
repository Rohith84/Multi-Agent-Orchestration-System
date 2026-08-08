/**
 * AIOps Service — API Client for Centralized Model Registry, Intelligent Router, LLM Evaluations, User Feedback, Benchmarks, Drift Detection, and Self-Optimization Recommendations.
 */

import api from "@/lib/api";

export interface PaginatedResponse<T> {
  items: T[];
  total_records: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ModelRegistryItem {
  id: string;
  org_id: string;
  model_name: string;
  provider: string;
  version: string;
  is_local: boolean;
  capabilities: string[];
  supported_languages: string[];
  context_window: number;
  supports_vision: boolean;
  supports_tool_calling: boolean;
  supports_json: boolean;
  avg_latency_ms: number;
  avg_quality_score: number;
  avg_token_usage: number;
  avg_cost_per_1k: number;
  availability: number;
  health_status: string;
  recommended_agent_roles: string[];
  created_at: string;
}

export interface ModelRoutingLog {
  id: string;
  org_id: string;
  workflow_run_id: string;
  agent_role: string;
  task_type: string;
  reasoning_complexity: string;
  selected_model: string;
  fallback_model?: string;
  was_fallback_used: boolean;
  routing_reason: string;
  latency_ms: number;
  tokens_used: number;
  estimated_cost: number;
  created_at: string;
}

export interface RouteDecisionResponse {
  selected_model: string;
  fallback_model: string;
  routing_reason: string;
  reasoning_complexity: string;
  task_type: string;
  agent_role: string;
  workflow_run_id: string;
  fallback_chain: string[];
}

export interface EvaluationReport {
  id: string;
  org_id: string;
  workflow_run_id: string;
  agent_role: string;
  accuracy: number;
  completeness: number;
  correctness: number;
  reasoning: number;
  grounding: number;
  hallucination_risk: number;
  citation_quality: number;
  code_quality: number;
  safety: number;
  overall_score: number;
  summary: string;
  created_at: string;
}

export interface BenchmarkRun {
  id: string;
  org_id: string;
  suite_name: string;
  target_model: string;
  target_prompt_version: string;
  target_workflow: string;
  accuracy_score: number;
  latency_score: number;
  cost_score: number;
  overall_benchmark_score: number;
  metrics_json: Record<string, unknown>;
  duration_ms: number;
  created_at: string;
}

export interface DriftReport {
  id: string;
  org_id: string;
  drift_type: string;
  target_identifier: string;
  baseline_score: number;
  current_score: number;
  drift_delta: number;
  status: string;
  created_at: string;
}

export interface OptimizationRecommendation {
  id: string;
  org_id: string;
  category: string;
  target_id: string;
  recommended_action: string;
  score_impact_estimate: number;
  reasoning_summary: string;
  status: string;
  created_at: string;
}

/**
 * List registered LLMs in Centralized Model Registry.
 */
export async function fetchModels(): Promise<ModelRegistryItem[]> {
  const { data } = await api.get<PaginatedResponse<ModelRegistryItem>>("/api/models");
  return data.items || [];
}

/**
 * Register a new model.
 */
export async function registerModel(payload: {
  model_name: string;
  provider: string;
  context_window: number;
  supports_vision: boolean;
}): Promise<ModelRegistryItem> {
  const { data } = await api.post<ModelRegistryItem>("/api/models", payload);
  return data;
}

/**
 * Fetch routing decision logs.
 */
export async function fetchRoutingLogs(): Promise<ModelRoutingLog[]> {
  const { data } = await api.get<PaginatedResponse<ModelRoutingLog>>("/api/models/router");
  return data.items || [];
}

/**
 * Request dynamic model routing decision.
 */
export async function decideModelRoute(payload: {
  task_type: string;
  agent_role: string;
  reasoning_complexity: string;
  vision_required: boolean;
}): Promise<RouteDecisionResponse> {
  const { data } = await api.post<RouteDecisionResponse>("/api/models/router/decide", payload);
  return data;
}

/**
 * Fetch LLM Agent evaluations.
 */
export async function fetchEvaluations(): Promise<EvaluationReport[]> {
  const { data } = await api.get<PaginatedResponse<EvaluationReport>>("/api/evaluations");
  return data.items || [];
}

/**
 * Submit user feedback.
 */
export async function submitFeedback(payload: {
  workflow_run_id: string;
  rating_type: string;
  rating_score: number;
  feedback_text: string;
}): Promise<{ id: string }> {
  const { data } = await api.post<{ id: string }>("/api/feedback", payload);
  return data;
}

/**
 * Fetch automated benchmarks.
 */
export async function fetchBenchmarks(): Promise<BenchmarkRun[]> {
  const { data } = await api.get<PaginatedResponse<BenchmarkRun>>("/api/benchmarks");
  return data.items || [];
}

/**
 * Trigger benchmark run.
 */
export async function runBenchmark(payload: {
  suite_name: string;
  target_model: string;
}): Promise<BenchmarkRun> {
  const { data } = await api.post<BenchmarkRun>("/api/benchmarks/run", payload);
  return data;
}

/**
 * Fetch drift detection reports.
 */
export async function fetchDriftReports(): Promise<DriftReport[]> {
  const { data } = await api.get<PaginatedResponse<DriftReport>>("/api/drift");
  return data.items || [];
}

/**
 * Fetch self-optimization recommendations.
 */
export async function fetchOptimizationRecommendations(): Promise<OptimizationRecommendation[]> {
  const { data } = await api.get<PaginatedResponse<OptimizationRecommendation>>("/api/optimizations");
  return data.items || [];
}
