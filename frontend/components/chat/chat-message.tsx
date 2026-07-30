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
        className={`relative max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-gradient-to-br from-violet-600 to-blue-600 text-white shadow-lg shadow-violet-500/20"
            : "bg-zinc-800/80 text-zinc-100 border border-zinc-700/50 shadow-md"
        }`}
      >
        {/* Content */}
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-700 prose-code:text-emerald-400 prose-code:before:content-none prose-code:after:content-none prose-headings:text-zinc-100 prose-a:text-blue-400">
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
            className={`text-[10px] ${
              isUser ? "text-white/50" : "text-zinc-500"
            }`}
          >
            {formattedTime}
            {!isUser && model && ` · ${model}`}
          </span>

          {!isUser && (
            <button
              onClick={handleCopy}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-zinc-700"
              title="Copy message"
            >
              {copied ? (
                <Check className="h-3 w-3 text-emerald-400" />
              ) : (
                <Copy className="h-3 w-3 text-zinc-500" />
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
