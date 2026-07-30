/**
 * ChatWindow — main scrollable message area.
 *
 * Features:
 * - Auto-scroll to bottom on new messages
 * - Empty state with welcome message
 * - Typing indicator while AI responds
 */

"use client";

import { useRef, useEffect } from "react";
import { Bot, Sparkles } from "lucide-react";
import { ChatMessageBubble } from "./chat-message";
import type { LocalMessage } from "@/hooks/use-chat";

interface ChatWindowProps {
  messages: LocalMessage[];
  isStreaming: boolean;
}

export function ChatWindow({ messages, isStreaming }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  // Empty state
  if (messages.length === 0) {
    return (
      <div
        ref={scrollRef}
        className="flex-1 flex items-center justify-center overflow-y-auto"
      >
        <div className="text-center space-y-6 max-w-md px-6">
          {/* Animated icon */}
          <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-600/20 to-blue-500/20 border border-violet-500/20 flex items-center justify-center shadow-xl shadow-violet-500/10">
            <Bot className="h-10 w-10 text-violet-400" />
          </div>

          <div>
            <h2 className="text-xl font-semibold text-white mb-2">
              AI Assistant
            </h2>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Ask me anything — I can help with coding, debugging, architecture,
              explanations, and more.
            </p>
          </div>

          {/* Suggestion chips */}
          <div className="flex flex-wrap justify-center gap-2">
            {[
              "Explain FastAPI dependency injection",
              "Write a Python async function",
              "What is the Repository pattern?",
            ].map((suggestion) => (
              <button
                key={suggestion}
                className="group flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-zinc-700/50 bg-zinc-800/50 text-xs text-zinc-400 hover:text-violet-300 hover:border-violet-500/30 hover:bg-violet-500/10 transition-all"
              >
                <Sparkles className="h-3 w-3 text-violet-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto py-4">
        {messages.map((msg) => (
          <ChatMessageBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            timestamp={msg.timestamp}
            model={msg.model}
          />
        ))}

        {/* Typing indicator */}
        {isStreaming && (
          <div className="flex gap-3 px-6 py-4">
            <div className="flex-shrink-0 mt-1">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shadow-md">
                <Bot className="h-4 w-4 text-white" />
              </div>
            </div>
            <div className="bg-zinc-800/80 border border-zinc-700/50 rounded-2xl px-4 py-3 shadow-md">
              <div className="flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full bg-violet-400 animate-bounce [animation-delay:-0.3s]" />
                <div className="h-2 w-2 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.15s]" />
                <div className="h-2 w-2 rounded-full bg-emerald-400 animate-bounce" />
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
