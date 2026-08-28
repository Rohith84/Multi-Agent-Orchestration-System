/**
 * ChatHeader — header bar for the chat interface.
 *
 * Displays the assistant title, model badge,
 * and action buttons for new chat / clear history.
 */

"use client";

import { Bot, Plus, Trash2, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ChatHeaderProps {
  sessionId: string | null;
  onNewChat: () => void;
  onClearChat: () => void;
  showExport?: boolean;
}

export function ChatHeader({
  sessionId,
  onNewChat,
  onClearChat,
  showExport = false,
}: ChatHeaderProps) {

  const handleExportZip = () => {
    if (!sessionId) return;
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    window.open(`${backendUrl}/api/workspace/export-zip?session_id=${encodeURIComponent(sessionId)}`, "_blank");
  };

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
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {sessionId && showExport && (
          <Button
            id="export-zip-btn"
            variant="outline"
            size="sm"
            onClick={handleExportZip}
            className="text-xs font-bold border-2 transition-all flex items-center gap-1"
            style={{
              borderColor: "var(--accent-secondary)",
              color: "var(--accent-secondary)",
              background: "var(--bg-surface)",
            }}
          >
            <Download className="h-4 w-4" />
            Export Code (.zip)
          </Button>
        )}

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
