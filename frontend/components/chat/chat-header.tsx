/**
 * ChatHeader — header bar for the chat interface.
 *
 * Displays the assistant title, model badge,
 * and action buttons for new chat / clear history.
 */

"use client";

import { Bot, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

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
  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-md">
      <div className="flex items-center gap-3">
        {/* AI icon */}
        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
          <Bot className="h-5 w-5 text-white" />
        </div>

        <div>
          <h1 className="text-lg font-semibold text-white">AI Assistant</h1>
          <div className="flex items-center gap-2 mt-0.5">
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 border-violet-500/30 text-violet-400"
            >
              Multi-Agent Graph
            </Badge>
            {sessionId && (
              <span className="text-[10px] text-zinc-600 font-mono">
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
          className="border-zinc-700 text-zinc-400 hover:text-white hover:bg-zinc-800 hover:border-zinc-600 transition-all"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          New Chat
        </Button>

        {sessionId && (
          <Button
            id="clear-chat-btn"
            variant="outline"
            size="sm"
            onClick={onClearChat}
            className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300 hover:border-red-500/50 transition-all"
          >
            <Trash2 className="h-4 w-4 mr-1.5" />
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
