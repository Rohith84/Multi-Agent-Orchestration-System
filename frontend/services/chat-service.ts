/**
 * Chat and Agent service — API calls for chat and multi-agent endpoints.
 */

import api from "@/lib/api";

/** Request body for POST /api/chat and /api/agents/chat */
export interface ChatRequest {
  message: string;
  session_id?: string;
}

/** Response from POST /api/chat */
export interface ChatResponse {
  response: string;
  session_id: string;
  model: string;
  created_at: string;
}

/** A single chat message */
export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  message: string;
  model: string | null;
  created_at: string;
}

/** Response from GET /api/chat/{session_id} */
export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
  message_count: number;
}

/** Response from DELETE /api/chat/{session_id} */
export interface ChatDeleteResponse {
  message: string;
  session_id: string;
  deleted_count: number;
}

/** Individual Agent Execution record */
export interface AgentExecution {
  id: string;
  session_id: string;
  agent_name: string;
  input_content: string;
  output_content: string;
  execution_time: number;
  status: string;
  created_at: string;
}

/** Response from GET /api/agents/history/{session_id} */
export interface AgentHistoryResponse {
  session_id: string;
  chat_history: ChatMessage[];
  agent_executions: AgentExecution[];
  execution_order: string[];
}

/** Response from DELETE /api/agents/history/{session_id} */
export interface AgentDeleteResponse {
  message: string;
  session_id: string;
  deleted_messages: number;
  deleted_executions: number;
}

/**
 * Send a message to the single AI assistant.
 * POST /api/chat
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/api/chat", request, {
    timeout: 120000,
  });
  return data;
}

/**
 * Fetch chat history for a session.
 * GET /api/chat/{session_id}
 */
export async function fetchChatHistory(
  sessionId: string
): Promise<ChatHistoryResponse> {
  const { data } = await api.get<ChatHistoryResponse>(
    `/api/chat/${sessionId}`
  );
  return data;
}

/**
 * Delete a chat session.
 * DELETE /api/chat/{session_id}
 */
export async function deleteChatSession(
  sessionId: string
): Promise<ChatDeleteResponse> {
  const { data } = await api.delete<ChatDeleteResponse>(
    `/api/chat/${sessionId}`
  );
  return data;
}

/**
 * Fetch aggregated multi-agent history for a session.
 * GET /api/agents/history/{session_id}
 */
export async function fetchAgentHistory(
  sessionId: string
): Promise<AgentHistoryResponse> {
  const { data } = await api.get<AgentHistoryResponse>(
    `/api/agents/history/${sessionId}`
  );
  return data;
}

/**
 * Delete aggregated multi-agent history for a session.
 * DELETE /api/agents/history/{session_id}
 */
export async function deleteAgentHistory(
  sessionId: string
): Promise<AgentDeleteResponse> {
  const { data } = await api.delete<AgentDeleteResponse>(
    `/api/agents/history/${sessionId}`
  );
  return data;
}
