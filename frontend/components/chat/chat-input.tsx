/**
 * ChatInput — message input area with send button.
 *
 * Features:
 * - Auto-resizing textarea
 * - Enter to send, Shift+Enter for newline
 * - Disabled while waiting for response
 * - Send button with loading state
 */

"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSend: (message: string, mode: ChatMode) => void;
  disabled: boolean;
  value?: string;
  onChangeValue?: (val: string) => void;
}

export type ChatMode = "ask" | "build";

export function ChatInput({ onSend, disabled, value, onChangeValue }: ChatInputProps) {
  const [internalInput, setInternalInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("ask");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const input = value !== undefined ? value : internalInput;

  const setInput = useCallback(
    (val: string) => {
      setInternalInput(val);
      onChangeValue?.(val);
    },
    [onChangeValue]
  );

  // Focus and adjust height when value updates externally
  useEffect(() => {
    if (value !== undefined) {
      setInternalInput(value);
      if (value && textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [value]);

  // Auto-resize textarea
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [input, adjustHeight]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (trimmed && !disabled) {
      onSend(trimmed, mode);
      setInput("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  }, [input, disabled, onSend, setInput]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Focus input when not disabled
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  return (
    <div
      className="px-6 py-4 border-t transition-colors"
      style={{
        background: "var(--bg-secondary)",
        borderColor: "var(--border-primary)",
      }}
    >
      <div className="flex items-end gap-3 max-w-4xl mx-auto">
        <select
          aria-label="Response mode"
          value={mode}
          onChange={(event) => setMode(event.target.value as ChatMode)}
          disabled={disabled}
          className="h-[48px] border-2 px-2 text-xs font-black uppercase focus:outline-none disabled:opacity-50"
          style={{ background: "var(--bg-surface)", color: "var(--fg-primary)", borderColor: "var(--border-primary)" }}
        >
          <option value="ask">Ask</option>
          <option value="build">Build</option>
        </select>
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              disabled ? "Waiting for response..." : mode === "ask" ? "Ask for an explanation or advice..." : "Describe the change you want built..."
            }
            disabled={disabled}
            rows={1}
            style={{
              background: "var(--bg-surface)",
              color: "var(--fg-primary)",
              borderColor: "var(--border-primary)",
              boxShadow: "var(--shadow-brutalist-sm)",
            }}
            className="w-full resize-none rounded-xl border-2 px-4 py-3.5 pr-12 text-sm font-extrabold placeholder:text-[var(--fg-tertiary)] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[var(--accent-secondary)] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          />
        </div>

        <Button
          id="send-button"
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="h-[48px] w-[48px] rounded-xl border-2 text-black transition-all flex-shrink-0 flex items-center justify-center font-bold hover:scale-105 cursor-pointer"
          style={{
            background: "var(--accent-primary)",
            color: "#111111",
            borderColor: "var(--border-primary)",
            boxShadow: "var(--shadow-brutalist-sm)",
          }}
          size="icon"
        >
          {disabled ? (
            <Loader2 className="h-5 w-5 animate-spin text-black" />
          ) : (
            <Send className="h-5 w-5 text-black" />
          )}
        </Button>
      </div>

      <p
        className="text-center text-[10px] font-mono font-bold mt-2 tracking-wide"
        style={{ color: "var(--fg-secondary)" }}
      >
        Press Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
