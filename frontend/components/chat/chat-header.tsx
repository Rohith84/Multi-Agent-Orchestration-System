/**
 * ChatHeader — header bar for the chat interface.
 *
 * Displays the assistant title, model badge,
 * and action buttons for new chat / clear history.
 */

"use client";

import { useState, useEffect } from "react";
import { Bot, Plus, Trash2, Cpu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";

interface ChatHeaderProps {
  sessionId: string | null;
  onNewChat: () => void;
  onClearChat: () => void;
}

export function ChatHeader({
  sessionId,
  onNewChat,
  onClearChat,
}: ChatHeaderProps) {
  const [ollamaProcessor, setOllamaProcessor] = useState<string>("checking...");

  useEffect(() => {
    let active = true;
    const checkRuntime = async () => {
      try {
        const { data } = await api.get("/api/ollama/runtime");
        if (active) {
          setOllamaProcessor(data.processor || "unknown");
        }
      } catch {
        if (active) setOllamaProcessor("unknown");
      }
    };
    checkRuntime();
    const interval = setInterval(checkRuntime, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);
  return (
    <div
      className="flex items-center justify-between px-6 py-4 border-b transition-colors"
      style={{
        background: "var(--bg-surface)",
        borderColor: "var(--border-secondary)",
      }}
    >
      <div className="flex items-center gap-3">
        {/* AI icon */}
        <div
          className="h-10 w-10 border-2 border-[var(--border-primary)] flex items-center justify-center shadow-[var(--shadow-brutalist-sm)]"
          style={{ background: "var(--accent-secondary)", color: "#FFFFFF" }}
        >
          <Bot className="h-5 w-5" />
        </div>

        <div>
          <h1
            className="text-lg font-black tracking-tight"
            style={{ color: "var(--fg-primary)" }}
          >
            AI Assistant
          </h1>
          <div className="flex items-center gap-2 mt-0.5">
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 border font-mono font-bold"
              style={{
                borderColor: "var(--border-primary)",
                background: "var(--bg-secondary)",
                color: "var(--fg-primary)",
              }}
            >
              Multi-Agent Graph
            </Badge>
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 border font-mono font-bold flex items-center gap-1"
              style={{
                borderColor: "var(--border-primary)",
                background: ollamaProcessor.includes("GPU") ? "var(--accent-lime, #a3e635)" : "var(--bg-secondary)",
                color: ollamaProcessor.includes("GPU") ? "#000000" : "var(--fg-primary)",
              }}
            >
              <Cpu className="h-3 w-3" /> Ollama: {ollamaProcessor.toUpperCase()}
            </Badge>
            {sessionId && (
              <span
                className="text-[10px] font-mono font-bold"
                style={{ color: "var(--fg-tertiary)" }}
              >
                {sessionId.slice(0, 8)}…
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          id="new-chat-btn"
          variant="outline"
          size="sm"
          onClick={onNewChat}
          className="brutalist-btn brutalist-btn-secondary text-xs"
        >
          <Plus className="h-4 w-4 mr-1" />
          New Chat
        </Button>

        {sessionId && (
          <Button
            id="clear-chat-btn"
            variant="outline"
            size="sm"
            onClick={onClearChat}
            className="text-xs font-bold border-2 transition-all"
            style={{
              borderColor: "var(--accent-error)",
              color: "var(--accent-error)",
              background: "var(--bg-surface)",
            }}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
