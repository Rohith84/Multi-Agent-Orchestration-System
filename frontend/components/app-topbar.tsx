/**
 * AppTopbar — Shared top header for /app/* routes.
 *
 * Displays:
 * - Breadcrumb path navigation
 * - Search / Command Palette shortcut indicator (⌘K)
 * - Real-time Backend Health dot (from useSystemStatus)
 * - Non-fabricated Workspace context indicator
 * - Theme switcher cycle button
 * - Mobile menu toggle
 */

"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Sun, Moon, Monitor, Search, Menu, ChevronRight } from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { useSystemStatus } from "@/hooks/use-system-status";

interface AppTopbarProps {
  onOpenMobileMenu?: () => void;
}

export function AppTopbar({ onOpenMobileMenu }: AppTopbarProps) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { data, isLoading, isError } = useSystemStatus();

  // Generate breadcrumbs from path
  const segments = pathname.split("/").filter(Boolean);

  const cycleTheme = () => {
    const order: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];
    const idx = order.indexOf(theme);
    setTheme(order[(idx + 1) % order.length]);
  };

  const ThemeIcon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  const isHealthy = data?.system_ready && !isError;

  return (
    <header className="h-14 border-b-2 border-[var(--border-primary)] flex items-center justify-between px-4 sm:px-6 shrink-0"
            style={{ background: "var(--bg-primary)" }}>

      {/* Left — Mobile toggle + Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="md:hidden w-8 h-8 flex items-center justify-center border-2 border-[var(--border-primary)]"
          style={{ background: "var(--bg-surface)", color: "var(--fg-primary)" }}
          aria-label="Open sidebar menu"
        >
          <Menu className="w-4 h-4" />
        </button>

        {/* Breadcrumb Navigation */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider">
          <Link href="/app" className="text-[var(--fg-secondary)] hover:text-[var(--fg-primary)] transition-colors">
            App
          </Link>
          {segments.slice(1).map((seg, idx) => {
            const path = "/app/" + segments.slice(1, idx + 2).join("/");
            return (
              <span key={path} className="flex items-center gap-1.5">
                <ChevronRight className="w-3 h-3 text-[var(--fg-tertiary)]" />
                <Link
                  href={path}
                  className={idx === segments.length - 2 ? "text-[var(--accent-secondary)]" : "text-[var(--fg-secondary)] hover:text-[var(--fg-primary)]"}
                >
                  {seg.replace("-", " ")}
                </Link>
              </span>
            );
          })}
        </nav>
      </div>

      {/* Right — Actions & Indicators */}
      <div className="flex items-center gap-2 sm:gap-3">

        {/* Command Search Shortcut Indicator */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 border-2 border-[var(--border-secondary)] bg-[var(--bg-surface)] text-[var(--fg-tertiary)] text-xs">
          <Search className="w-3.5 h-3.5" />
          <span className="font-mono text-[10px]">⌘K Search</span>
        </div>

        {/* System Health Dot */}
        <div className="flex items-center gap-1.5 px-2 py-1 border-2 border-[var(--border-secondary)] bg-[var(--bg-surface)]"
             title={isLoading ? "Checking system..." : isHealthy ? "All systems operational" : "Backend unreachable"}>
          <div className={`status-dot ${isLoading ? "status-dot-warning" : isHealthy ? "status-dot-online" : "status-dot-offline"}`} />
          <span className="hidden lg:inline text-[10px] font-bold uppercase text-[var(--fg-secondary)]">
            {isLoading ? "Checking" : isHealthy ? "Online" : "Offline"}
          </span>
        </div>

        {/* Workspace Context Indicator (Non-fabricated) */}
        <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 border-2 border-[var(--border-secondary)] bg-[var(--bg-surface)] text-[10px] font-mono font-bold text-[var(--fg-secondary)]">
          <span>WS: default</span>
        </div>

        {/* Theme Cycle Button */}
        <button
          onClick={cycleTheme}
          className="w-8 h-8 flex items-center justify-center border-2 border-[var(--border-primary)] transition-transform hover:translate-x-[-1px] hover:translate-y-[-1px]"
          style={{
            background: "var(--bg-surface)",
            boxShadow: "var(--shadow-brutalist-sm)",
            color: "var(--fg-primary)",
          }}
          aria-label={`Current theme: ${theme}. Click to cycle.`}
        >
          <ThemeIcon className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
}
