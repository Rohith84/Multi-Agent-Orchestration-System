/**
 * ChatMessage — individual message bubble component.
 *
 * Renders user and assistant messages with distinct styles.
 * Assistant messages support markdown rendering.
 */

"use client";

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Bot, Copy, Check } from "lucide-react";
import { useState, useCallback } from "react";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  model?: string | null;
}

export const ChatMessageBubble = memo(function ChatMessageBubble({
  role,
  content,
  timestamp,
  model,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error("Failed to copy");
    }
  }, [content]);

  const formattedTime = (() => {
    try {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  })();

  return (
    <div
      className={`flex gap-3 px-6 py-4 group transition-colors ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div className="flex-shrink-0 mt-1">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shadow-md">
            <Bot className="h-4 w-4 text-white" />
          </div>
        </div>
      )}

      {/* Message bubble */}
      <div
        className={`relative max-w-[75%] rounded-2xl px-4 py-3 border-2 ${
          isUser
            ? "border-[var(--border-primary)] shadow-[var(--shadow-brutalist-sm)]"
            : "border-[var(--border-primary)] shadow-[var(--shadow-brutalist-sm)]"
        }`}
        style={
          isUser
            ? {
                background: "var(--accent-secondary)",
                color: "#FFFFFF",
                borderColor: "var(--border-primary)",
              }
            : {
                background: "var(--bg-surface)",
                color: "var(--fg-primary)",
                borderColor: "var(--border-primary)",
              }
        }
      >
        {/* Content */}
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap font-medium">{content}</p>
        ) : (
          <div className="prose prose-sm max-w-none leading-relaxed text-[var(--fg-primary)]">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}

        {/* Footer: timestamp + copy */}
        <div
          className={`flex items-center gap-2 mt-2 ${
            isUser ? "justify-end" : "justify-between"
          }`}
        >
          <span
            className="text-[10px] font-mono font-bold"
            style={{ color: isUser ? "rgba(255,255,255,0.8)" : "var(--fg-tertiary)" }}
          >
            {formattedTime}
            {!isUser && model && ` · ${model}`}
          </span>

          {!isUser && (
            <button
              onClick={handleCopy}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded border border-[var(--border-secondary)] hover:bg-[var(--bg-secondary)]"
              title="Copy message"
            >
              {copied ? (
                <Check className="h-3 w-3 text-[var(--accent-success)]" />
              ) : (
                <Copy className="h-3 w-3 text-[var(--fg-secondary)]" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 mt-1">
          <div className="h-8 w-8 rounded-lg bg-zinc-700 flex items-center justify-center">
            <User className="h-4 w-4 text-zinc-300" />
          </div>
        </div>
      )}
    </div>
  );
});
