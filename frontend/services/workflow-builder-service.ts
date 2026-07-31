/**
 * Workflow Builder Service — API client for dynamic templates, custom agents, graph validation, simulation, and execution.
 */

import api from "@/lib/api";

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  config?: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  graph_json: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  version: number;
  is_preset: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomAgent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  user_prompt_template: string;
  llm_model: string;
  temperature: number;
  retry_count: number;
  allowed_mcp_tools: string[];
  created_at: string;
}

export interface SimulationReport {
  execution_order: string[];
  estimated_runtime_seconds: number;
  potential_failures: string[];
}

/**
 * List workflow templates.
 * GET /api/workflows/templates
 */
export async function fetchWorkflowTemplates(): Promise<WorkflowTemplate[]> {
  const { data } = await api.get<WorkflowTemplate[]>("/api/workflows/templates");
  return data;
}

/**
 * Create custom workflow template.
 * POST /api/workflows/templates
 */
export async function createWorkflowTemplate(payload: {
  name: string;
  description: string;
  graph_json: { nodes: GraphNode[]; edges: GraphEdge[] };
}): Promise<WorkflowTemplate> {
  const { data } = await api.post<WorkflowTemplate>("/api/workflows/templates", payload);
  return data;
}

/**
 * Dry-run simulation of workflow.
 * POST /api/workflows/builder/{id}/simulate
 */
export async function simulateWorkflowTemplate(templateId: string): Promise<SimulationReport> {
  const { data } = await api.post<SimulationReport>(`/api/workflows/builder/${templateId}/simulate`);
  return data;
}

/**
 * Execute dynamic workflow graph.
 * POST /api/workflows/builder/{id}/execute
 */
export async function executeDynamicWorkflow(templateId: string, userRequest: string): Promise<Record<string, unknown>> {
  const { data } = await api.post<Record<string, unknown>>(`/api/workflows/builder/${templateId}/execute`, null, {
    params: { user_request: userRequest },
  });
  return data;
}

/**
 * List custom agents.
 * GET /api/custom-agents
 */
export async function fetchCustomAgents(): Promise<CustomAgent[]> {
  const { data } = await api.get<CustomAgent[]>("/api/custom-agents");
  return data;
}

/**
 * Create custom agent.
 * POST /api/custom-agents
 */
export async function createCustomAgent(payload: {
  name: string;
  description: string;
  system_prompt: string;
  llm_model?: string;
  temperature?: number;
  allowed_mcp_tools?: string[];
}): Promise<CustomAgent> {
  const { data } = await api.post<CustomAgent>("/api/custom-agents", payload);
  return data;
}
