/**
 * AppNavbar — Global top navigation for MultiAgent OS.
 *
 * Compact neo-brutalist header with:
 * - Product wordmark
 * - Route navigation links
 * - Theme toggle (light/dark/system)
 * - Get Started CTA
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun, Moon, Monitor, Menu, X } from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { useState } from "react";

const NAV_LINKS = [
  { label: "Overview", href: "/" },
  { label: "Agents", href: "/chat" },
  { label: "Workflows", href: "/workflows" },
  { label: "Tools", href: "/tools" },
  { label: "Analytics", href: "/analytics" },
];

export function AppNavbar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  const cycleTheme = () => {
    const order: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];
    const idx = order.indexOf(theme);
    setTheme(order[(idx + 1) % order.length]);
  };

  const ThemeIcon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;

  return (
    <nav className="sticky top-0 z-50 border-b-2 border-[var(--border-primary)]"
         style={{ background: "var(--bg-primary)" }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">

          {/* Left — Wordmark */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 border-2 border-[var(--border-primary)] flex items-center justify-center"
                 style={{ background: "var(--accent-primary)" }}>
              <span className="text-[10px] font-black text-[var(--fg-on-accent)] leading-none">M</span>
            </div>
            <span className="text-sm font-extrabold tracking-tight uppercase"
                  style={{ color: "var(--fg-primary)" }}>
              MultiAgent OS
            </span>
          </Link>

          {/* Center — Nav Links (desktop) */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className="px-3 py-1.5 text-xs font-bold uppercase tracking-wide transition-colors"
                  style={{
                    color: isActive ? "var(--fg-on-accent)" : "var(--fg-secondary)",
                    background: isActive ? "var(--accent-primary)" : "transparent",
                  }}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>

          {/* Right — Controls */}
          <div className="flex items-center gap-2">
            {/* Theme Toggle */}
            <button
              onClick={cycleTheme}
              className="w-8 h-8 flex items-center justify-center border-2 border-[var(--border-primary)] transition-all hover:translate-x-[-1px] hover:translate-y-[-1px]"
              style={{
                background: "var(--bg-surface)",
                boxShadow: "var(--shadow-brutalist-sm)",
                color: "var(--fg-primary)",
              }}
              aria-label={`Current theme: ${theme}. Click to cycle.`}
            >
              <ThemeIcon className="w-3.5 h-3.5" />
            </button>

            {/* Get Started CTA (desktop) */}
            <Link
              href="/app/chat"
              className="hidden sm:inline-flex brutalist-btn brutalist-btn-primary text-[11px] py-1.5 px-4"
            >
              Get Started
            </Link>

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden w-8 h-8 flex items-center justify-center border-2 border-[var(--border-primary)]"
              style={{
                background: "var(--bg-surface)",
                color: "var(--fg-primary)",
              }}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileOpen && (
        <div className="md:hidden border-t-2 border-[var(--border-primary)] animate-fade-in"
             style={{ background: "var(--bg-surface)" }}>
          <div className="px-4 py-4 space-y-1">
            {NAV_LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="block px-3 py-2 text-sm font-bold uppercase tracking-wide"
                  style={{
                    color: isActive ? "var(--fg-on-accent)" : "var(--fg-primary)",
                    background: isActive ? "var(--accent-primary)" : "transparent",
                  }}
                >
                  {link.label}
                </Link>
              );
            })}
            <div className="pt-3 border-t border-[var(--border-secondary)]">
              <Link
                href="/app/chat"
                onClick={() => setMobileOpen(false)}
                className="brutalist-btn brutalist-btn-primary w-full text-center text-xs"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
