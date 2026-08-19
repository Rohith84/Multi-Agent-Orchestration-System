/**
 * React hook for AI chat functionality supporting the Multi-Agent Orchestration workflow.
 * Uses fetch with ReadableStream to support POST-based Server-Sent Events (SSE) streaming.
 */

"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  fetchAgentHistory,
  deleteAgentHistory,
  sendChatMessage,
  type ChatMessage,
  type AgentExecution,
} from "@/services/chat-service";
import type { ChatMode } from "@/components/chat/chat-input";

const LAST_SESSION_STORAGE_KEY = "multiagent:last-chat-session";

export interface LocalMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string | null;
  timestamp: string;
}

export interface UIExecutionState {
  agentName: string;
  status: "idle" | "running" | "retrying" | "success" | "failed";
  output: string;
  executionTime: number;
  toolInvocations: ToolInvocationUI[];
}

export interface ToolInvocationUI {
  agent: string;
  toolName: string;
  status: string;
  executionTime: number;
}

const INITIAL_EXECUTIONS: Record<string, UIExecutionState> = {
  planner: { agentName: "planner", status: "idle", output: "", executionTime: 0, toolInvocations: [] },
  research: { agentName: "research", status: "idle", output: "", executionTime: 0, toolInvocations: [] },
  coder: { agentName: "coder", status: "idle", output: "", executionTime: 0, toolInvocations: [] },
  tester: { agentName: "tester", status: "idle", output: "", executionTime: 0, toolInvocations: [] },
  reviewer: { agentName: "reviewer", status: "idle", output: "", executionTime: 0, toolInvocations: [] },
};

export function useChat() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [executions, setExecutions] = useState<Record<string, UIExecutionState>>(INITIAL_EXECUTIONS);
  const queryClient = useQueryClient();
  const messageIdCounter = useRef(0);

  const rememberSession = useCallback((sid: string) => {
    setSessionId(sid);
    window.localStorage.setItem(LAST_SESSION_STORAGE_KEY, sid);
    window.history.replaceState(null, "", `/app/chat?session=${encodeURIComponent(sid)}`);
  }, []);

  const generateLocalId = () => {
    messageIdCounter.current += 1;
    return `local-${Date.now()}-${messageIdCounter.current}`;
  };

  // Start a new conversation
  const newChat = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setActiveAgent(null);
    setIsPending(false);
    setExecutions(INITIAL_EXECUTIONS);
    window.localStorage.removeItem(LAST_SESSION_STORAGE_KEY);
    window.history.replaceState(null, "", "/app/chat");
    queryClient.invalidateQueries({ queryKey: ["chat-history"] });
  }, [queryClient]);

  // Load history for a session
  const loadHistory = useCallback(
    async (sid: string) => {
      try {
        const history = await fetchAgentHistory(sid);
        rememberSession(sid);

        const localMessages: LocalMessage[] = history.chat_history
          .map((msg: ChatMessage) => ({
            id: msg.id,
            role: msg.role as "user" | "assistant",
            content: msg.message,
            model: msg.model,
            timestamp: msg.created_at,
          }));
        setMessages(localMessages);

        // Populate executions from history
        const newExecutions = { ...INITIAL_EXECUTIONS };
        history.agent_executions.forEach((ex: AgentExecution) => {
          newExecutions[ex.agent_name] = {
            agentName: ex.agent_name,
            status: ex.status as any,
            output: ex.output_content,
            executionTime: ex.execution_time,
            toolInvocations: [],
          };
        });
        setExecutions(newExecutions);
      } catch (error) {
        console.error("Failed to load chat history:", error);
      }
    },
    [rememberSession]
  );

  useEffect(() => {
    const querySession = new URLSearchParams(window.location.search).get("session");
    const rememberedSession = window.localStorage.getItem(LAST_SESSION_STORAGE_KEY);
    const sid = querySession || rememberedSession;
    if (sid) void loadHistory(sid);
  }, [loadHistory]);

  // Delete current session
  const clearChat = useCallback(async () => {
    if (sessionId) {
      try {
        await deleteAgentHistory(sessionId);
      } catch (error) {
        console.error("Failed to delete chat session:", error);
      }
    }
    newChat();
  }, [sessionId, newChat]);

  // Send a message via SSE streaming
  const sendMessage = useCallback(
    async (messageText: string, mode: ChatMode = "ask") => {
      if (!messageText.trim() || isPending) return;

      setIsPending(true);
      setExecutions(INITIAL_EXECUTIONS);

      // Add user message optimistically
      const userMsg: LocalMessage = {
        id: generateLocalId(),
        role: "user",
        content: messageText,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        if (mode === "ask") {
          const result = await sendChatMessage({
            message: messageText,
            session_id: sessionId || undefined,
          });
          rememberSession(result.session_id);
          setMessages((prev) => [
            ...prev,
            {
              id: generateLocalId(),
              role: "assistant",
              content: result.response,
              model: result.model,
              timestamp: result.created_at,
            },
          ]);
          return;
        }

        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${API_URL}/api/agents/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: messageText,
            session_id: sessionId || undefined,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) throw new Error("ReadableStream not supported by response");

        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Split buffer by double newlines (SSE format)
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || ""; // Keep the incomplete last block in buffer

          for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed || !trimmed.startsWith("data: ")) continue;

            const jsonStr = trimmed.replace("data: ", "");
            try {
              const data = JSON.parse(jsonStr);

              switch (data.event) {
                case "workflow_started":
                  rememberSession(data.session_id);
                  break;

                case "agent_start":
                  setActiveAgent(data.agent);
                  setExecutions((prev) => ({
                    ...prev,
                    [data.agent]: {
                      ...prev[data.agent],
                      status: "running",
                    },
                  }));
                  break;

                case "agent_retry":
                  setExecutions((prev) => ({
                    ...prev,
                    [data.agent]: {
                      ...prev[data.agent],
                      status: "retrying",
                    },
                  }));
                  break;

                case "agent_end":
                  setExecutions((prev) => ({
                    ...prev,
                    [data.agent]: {
                      agentName: data.agent,
                      status: data.status as any,
                      output: data.output,
                      executionTime: data.execution_time,
                    },
                  }));
                  break;

                case "workflow_complete":
                  rememberSession(data.session_id);
                  setActiveAgent(null);
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: generateLocalId(),
                      role: "assistant",
                      content: data.response,
                      timestamp: new Date().toISOString(),
                    },
                  ]);
                  break;

                case "workflow_failed":
                  setActiveAgent(null);
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: generateLocalId(),
                      role: "assistant",
                      content: `Workflow failed: ${data.error}`,
                      timestamp: new Date().toISOString(),
                    },
                  ]);
                  break;

                case "workflow_paused_approval":
                  setActiveAgent(data.agent);
                  setExecutions((prev) => ({
                    ...prev,
                    [data.agent]: {
                      ...prev[data.agent],
                      status: "paused_approval" as any,
                      output: `Waiting for human approval: ${data.message}`,
                    },
                  }));
                  break;

                case "tool_execution":
                  setExecutions((prev) => {
                    const agent = data.agent;
                    if (!prev[agent]) return prev;
                    return {
                      ...prev,
                      [agent]: {
                        ...prev[agent],
                        toolInvocations: [
                          ...prev[agent].toolInvocations,
                          {
                            agent: data.agent,
                            toolName: data.tool_name,
                            status: data.status,
                            executionTime: data.execution_time,
                          },
                        ],
                      },
                    };
                  });
                  break;
              }
            } catch (err) {
              console.error("Error parsing stream chunk:", err, jsonStr);
            }
          }
        }
      } catch (err: any) {
        console.error("Stream execution error:", err);
        setMessages((prev) => [
          ...prev,
          {
            id: generateLocalId(),
            role: "assistant",
            content: "Sorry, I encountered an error communicating with the agent workflow. Please ensure Ollama and the backend are running.",
            timestamp: new Date().toISOString(),
          },
        ]);
        setActiveAgent(null);
      } finally {
        setIsPending(false);
      }
    },
    [sessionId, isPending, rememberSession]
  );

  return {
    messages,
    sessionId,
    activeAgent,
    isPending,
    executions,
    sendMessage,
    newChat,
    clearChat,
    loadHistory,
  };
}
