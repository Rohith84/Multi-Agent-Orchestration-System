/**
 * Chat page — AI assistant interface.
 *
 * Full-screen chat experience side-by-side with:
 * - Chat header with model info and actions
 * - Scrollable message window
 * - Input area with auto-resize
 * - Multi-agent timeline progress tracker panel
 */

"use client";

import { ChatHeader } from "@/components/chat/chat-header";
import { ChatWindow } from "@/components/chat/chat-window";
import { ChatInput } from "@/components/chat/chat-input";
import { AgentTimeline } from "@/components/chat/agent-timeline";
import { useChat } from "@/hooks/use-chat";

export default function ChatPage() {
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
    <div className="flex h-screen bg-zinc-950 overflow-hidden">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <ChatHeader
          sessionId={sessionId}
          onNewChat={newChat}
          onClearChat={clearChat}
        />
        <ChatWindow messages={messages} isStreaming={isPending && !activeAgent} />
        <ChatInput onSend={sendMessage} disabled={isPending} />
      </div>

      {/* Execution Timeline Panel */}
      <AgentTimeline executions={executions} activeAgent={activeAgent} />
    </div>
  );
}
