/**
 * PublicNavbar — Marketing site navigation for MultiAgent OS.
 *
 * Used only on public pages (/, /login, /signup).
 * Separate from AppNavbar (legacy) and AppTopbar/AppSidebar (authenticated shell).
 */

"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { Sun, Moon, Menu, X } from "lucide-react";
import { useTheme } from "@/components/theme-provider";

const SECTION_LINKS = [
  { label: "Product", href: "#capabilities" },
  { label: "How It Works", href: "#architecture" },
  { label: "Agents", href: "#agents" },
  { label: "Capabilities", href: "#platform" },
  { label: "Enterprise", href: "#governance" },
];

export function PublicNavbar() {
  const { theme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const cycleTheme = () => {
    const order: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];
    const idx = order.indexOf(theme);
    setTheme(order[(idx + 1) % order.length]);
  };

  const handleAnchorClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith("#")) {
      e.preventDefault();
      const el = document.getElementById(href.slice(1));
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      setMobileOpen(false);
    }
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "border-b-2 border-[var(--border-primary)]"
          : "border-b-2 border-transparent"
      }`}
      style={{
        background: scrolled ? "var(--bg-primary)" : "transparent",
        backdropFilter: scrolled ? "none" : "blur(8px)",
      }}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div
              className="w-8 h-8 border-2 border-[var(--border-primary)] flex items-center justify-center"
              style={{ background: "var(--accent-primary)" }}
            >
              <span className="text-[11px] font-black text-[var(--fg-on-accent)] leading-none">
                M
              </span>
            </div>
            <span
              className="text-sm font-extrabold tracking-tight uppercase"
              style={{ color: "var(--fg-primary)" }}
            >
              MultiAgent OS
            </span>
          </Link>

          {/* Center — Section Links (desktop) */}
          <div className="hidden lg:flex items-center gap-1">
            {SECTION_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleAnchorClick(e, link.href)}
                className="px-3 py-1.5 text-xs font-bold uppercase tracking-wide transition-colors hover:text-[var(--accent-primary)]"
                style={{ color: "var(--fg-secondary)" }}
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right — Controls */}
          <div className="flex items-center gap-2">
            {/* Theme Toggle */}
            <button
              onClick={cycleTheme}
              type="button"
              className="w-8 h-8 flex items-center justify-center border-2 border-[var(--border-primary)] transition-all hover:translate-x-[-1px] hover:translate-y-[-1px]"
              style={{
                background: "var(--bg-surface)",
                boxShadow: "var(--shadow-brutalist-sm)",
                color: "var(--fg-primary)",
              }}
              aria-label="Toggle theme"
            >
              <Sun className="w-3.5 h-3.5 dark:hidden" aria-hidden="true" />
              <Moon className="w-3.5 h-3.5 hidden dark:inline" aria-hidden="true" />
            </button>

            {/* Sign In (desktop) */}
            <Link
              href="/login"
              className="hidden sm:inline-flex px-4 py-1.5 text-[11px] font-bold uppercase tracking-wide transition-colors hover:text-[var(--accent-primary)]"
              style={{ color: "var(--fg-secondary)" }}
            >
              Sign In
            </Link>

            {/* Launch OS CTA (desktop) */}
            <Link
              href="/app"
              className="hidden sm:inline-flex brutalist-btn brutalist-btn-primary text-[11px] py-1.5 px-4"
            >
              Launch OS →
            </Link>

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              type="button"
              className="lg:hidden w-8 h-8 flex items-center justify-center border-2 border-[var(--border-primary)]"
              style={{
                background: "var(--bg-surface)",
                color: "var(--fg-primary)",
              }}
              aria-label="Toggle menu"
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? (
                <X className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Menu className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div
          className="lg:hidden border-t-2 border-[var(--border-primary)] animate-fade-in"
          style={{ background: "var(--bg-surface)" }}
        >
          <div className="px-4 py-4 space-y-1">
            {SECTION_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleAnchorClick(e, link.href)}
                className="block px-3 py-2 text-sm font-bold uppercase tracking-wide"
                style={{ color: "var(--fg-primary)" }}
              >
                {link.label}
              </a>
            ))}
            <div className="pt-3 mt-2 border-t border-[var(--border-secondary)] space-y-2">
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2 text-sm font-bold uppercase tracking-wide"
                style={{ color: "var(--fg-secondary)" }}
              >
                Sign In
              </Link>
              <Link
                href="/app"
                onClick={() => setMobileOpen(false)}
                className="brutalist-btn brutalist-btn-primary w-full text-center text-xs"
              >
                Launch OS →
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
