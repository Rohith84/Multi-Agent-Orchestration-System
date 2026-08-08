/**
 * /app/settings — Application Settings route.
 *
 * System preferences, API endpoints, theme controls, and local model settings.
 */

"use client";

import { useTheme } from "@/components/theme-provider";
import { Sliders, Sun, Moon, Monitor, Server, Database, Key } from "lucide-react";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="p-6 brutalist-card" style={{ background: "var(--bg-surface)" }}>
        <div className="inline-block mb-2">
          <span className="brutalist-btn-primary text-caption px-2.5 py-0.5 border"
                style={{ borderColor: "var(--border-primary)" }}>
            CONFIGURATION
          </span>
        </div>
        <h1 className="text-h1 font-black tracking-tight" style={{ color: "var(--fg-primary)" }}>
          Application Settings
        </h1>
        <p className="text-body-sm mt-1" style={{ color: "var(--fg-secondary)" }}>
          Manage local display preferences, system environment endpoints, and API configurations.
        </p>
      </div>

      {/* Theme Settings */}
      <div className="brutalist-card p-6" style={{ background: "var(--bg-surface)" }}>
        <h2 className="text-h3 font-extrabold uppercase mb-4" style={{ color: "var(--fg-primary)" }}>
          Appearance & Theme
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { mode: "light" as const, label: "Light Mode", icon: Sun },
            { mode: "dark" as const, label: "Dark Mode", icon: Moon },
            { mode: "system" as const, label: "System Default", icon: Monitor },
          ].map((item) => (
            <button
              key={item.mode}
              onClick={() => setTheme(item.mode)}
              className={`
                p-4 border-2 flex items-center gap-3 transition-all text-left
                ${theme === item.mode
                  ? "border-[var(--border-primary)] bg-[var(--accent-primary)] text-[var(--fg-on-accent)] shadow-[2px_2px_0px_0px_#111111]"
                  : "border-[var(--border-secondary)] bg-[var(--bg-primary)] text-[var(--fg-primary)] hover:border-[var(--border-primary)]"
                }
              `}
            >
              <item.icon className="w-5 h-5 shrink-0" />
              <div>
                <span className="text-xs font-bold uppercase block">{item.label}</span>
                <span className="text-[10px] opacity-80">{item.mode === theme ? "Active" : "Select"}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* System Endpoints */}
      <div className="brutalist-card p-6 space-y-4" style={{ background: "var(--bg-surface)" }}>
        <h2 className="text-h3 font-extrabold uppercase mb-2" style={{ color: "var(--fg-primary)" }}>
          System Endpoints
        </h2>

        <div className="space-y-3">
          <div className="p-3 border-2 border-[var(--border-secondary)] bg-[var(--bg-secondary)] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Server className="w-4 h-4 text-[var(--accent-secondary)]" />
              <div>
                <span className="text-xs font-bold uppercase block text-[var(--fg-primary)]">FastAPI Backend</span>
                <span className="text-caption text-[var(--fg-tertiary)]">NEXT_PUBLIC_API_URL</span>
              </div>
            </div>
            <code className="text-mono text-xs font-bold text-[var(--accent-success)]">http://localhost:8000</code>
          </div>

          <div className="p-3 border-2 border-[var(--border-secondary)] bg-[var(--bg-secondary)] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Database className="w-4 h-4 text-[var(--accent-tertiary)]" />
              <div>
                <span className="text-xs font-bold uppercase block text-[var(--fg-primary)]">PostgreSQL Database</span>
                <span className="text-caption text-[var(--fg-tertiary)]">multi_agent_db</span>
              </div>
            </div>
            <code className="text-mono text-xs font-bold text-[var(--accent-success)]">localhost:5432</code>
          </div>

          <div className="p-3 border-2 border-[var(--border-secondary)] bg-[var(--bg-secondary)] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Sliders className="w-4 h-4 text-[var(--accent-warning)]" />
              <div>
                <span className="text-xs font-bold uppercase block text-[var(--fg-primary)]">Ollama LLM Host</span>
                <span className="text-caption text-[var(--fg-tertiary)]">OLLAMA_BASE_URL</span>
              </div>
            </div>
            <code className="text-mono text-xs font-bold text-[var(--accent-success)]">http://localhost:11434</code>
          </div>
        </div>
      </div>

    </div>
  );
}
