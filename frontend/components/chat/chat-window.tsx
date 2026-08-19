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
  onSelectSuggestion?: (suggestion: string) => void;
}

export function ChatWindow({ messages, isStreaming, onSelectSuggestion }: ChatWindowProps) {
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
          <div
            className="mx-auto w-20 h-20 border-2 border-[var(--border-primary)] flex items-center justify-center shadow-[var(--shadow-brutalist)]"
            style={{ background: "var(--accent-secondary)", color: "#FFFFFF" }}
          >
            <Bot className="h-10 w-10" />
          </div>

          <div>
            <h2
              className="text-xl font-black mb-2 tracking-tight"
              style={{ color: "var(--fg-primary)" }}
            >
              AI Assistant
            </h2>
            <p
              className="text-sm font-medium leading-relaxed"
              style={{ color: "var(--fg-secondary)" }}
            >
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
                type="button"
                onClick={() => onSelectSuggestion?.(suggestion)}
                className="group flex items-center gap-1.5 px-3 py-2 border-2 text-xs font-extrabold transition-all hover:scale-105 cursor-pointer"
                style={{
                  background: "var(--bg-surface)",
                  color: "var(--fg-primary)",
                  borderColor: "var(--border-primary)",
                  boxShadow: "var(--shadow-brutalist-sm)",
                }}
              >
                <Sparkles
                  className="h-3.5 w-3.5 transition-transform group-hover:scale-110"
                  style={{ color: "var(--accent-secondary)" }}
                />
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
