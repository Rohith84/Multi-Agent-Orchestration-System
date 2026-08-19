/**
 * /app/chat — Canonical AI Assistant route inside the /app/* application shell.
 *
 * Features:
 * - Side-by-side Chat Header, Message Window, Input, and Agent Execution Timeline.
 * - Real-time SSE streaming powered by useChat hook.
 */

"use client";

import { useState } from "react";
import { ChatHeader } from "@/components/chat/chat-header";
import { ChatWindow } from "@/components/chat/chat-window";
import { ChatInput } from "@/components/chat/chat-input";
import { AgentTimeline } from "@/components/chat/agent-timeline";
import { useChat } from "@/hooks/use-chat";
import type { ChatMode } from "@/components/chat/chat-input";

export default function ChatPage() {
  const [draftInput, setDraftInput] = useState("");
  const {
    messages,
    sessionId,
    activeAgent,
    isPending,
    executions,
    sendMessage,
    newChat,
    clearChat,
  } = useChat();

  return (
    <div className="flex h-[calc(100vh-110px)] overflow-hidden brutalist-card" style={{ background: "var(--bg-surface)" }}>
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <ChatHeader
          sessionId={sessionId}
          onNewChat={newChat}
          onClearChat={clearChat}
        />
        <ChatWindow
          messages={messages}
          isStreaming={isPending && !activeAgent}
          onSelectSuggestion={(suggestion) => setDraftInput(suggestion)}
        />
        <ChatInput
          onSend={(message, mode: ChatMode) => sendMessage(message, mode)}
          disabled={isPending}
          value={draftInput}
          onChangeValue={setDraftInput}
        />
      </div>

      {/* Execution Timeline Panel */}
      <AgentTimeline executions={executions} activeAgent={activeAgent} />
    </div>
  );
}
