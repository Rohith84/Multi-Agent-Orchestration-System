/**
 * Tools service — API calls for MCP tool endpoints.
 */

import api from "@/lib/api";

/** Schema for an MCP tool definition */
export interface ToolDefinition {
  name: string;
  description: string;
  category: string;
  parameters: {
    properties: Record<string, { type: string; description: string }>;
    required: string[];
  };
}

/** Response from GET /api/tools */
export interface ToolListResponse {
  tools: ToolDefinition[];
  count: number;
}

/** Request for POST /api/tools/run */
export interface ToolRunRequest {
  tool_name: string;
  arguments: Record<string, unknown>;
  agent_name?: string;
}

/** Response from POST /api/tools/run */
export interface ToolRunResponse {
  success: boolean;
  tool_name: string;
  result: unknown;
  error: string | null;
  execution_time: number;
}

/** Tool execution history record */
export interface ToolExecution {
  id: string;
  agent_name: string;
  tool_name: string;
  arguments: string;
  status: string;
  execution_time: number;
  result_summary: string;
  created_at: string;
}

/** Response from GET /api/tools/history */
export interface ToolHistoryResponse {
  executions: ToolExecution[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Fetch all available MCP tools.
 * GET /api/tools
 */
export async function fetchTools(): Promise<ToolListResponse> {
  const { data } = await api.get<ToolListResponse>("/api/tools");
  return data;
}

/**
 * Execute an MCP tool manually.
 * POST /api/tools/run
 */
export async function executeTool(
  request: ToolRunRequest
): Promise<ToolRunResponse> {
  const { data } = await api.post<ToolRunResponse>("/api/tools/run", request, {
    timeout: 60000,
  });
  return data;
}

/**
 * Fetch tool execution history.
 * GET /api/tools/history
 */
export async function fetchToolHistory(params?: {
  limit?: number;
  offset?: number;
  search?: string;
}): Promise<ToolHistoryResponse> {
  const { data } = await api.get<ToolHistoryResponse>("/api/tools/history", {
    params,
  });
  return data;
}
