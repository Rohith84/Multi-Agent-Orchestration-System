/**
 * AppFooter — Global footer for MultiAgent OS.
 *
 * Compact brutalist footer with product links and copyright.
 */

"use client";

import Link from "next/link";

const FOOTER_SECTIONS = [
  {
    title: "Product",
    links: [
      { label: "Overview", href: "/" },
      { label: "Workflows", href: "/workflows" },
      { label: "Analytics", href: "/analytics" },
      { label: "Workspace", href: "/workspace" },
    ],
  },
  {
    title: "Agents",
    links: [
      { label: "AI Assistant", href: "/chat" },
      { label: "Agent Builder", href: "/workflow-builder" },
      { label: "Artifacts", href: "/artifacts" },
      { label: "AIOps", href: "/aiops" },
    ],
  },
  {
    title: "Platform",
    links: [
      { label: "Knowledge Base", href: "/knowledge" },
      { label: "Tool Center", href: "/tools" },
      { label: "Operations", href: "/operations" },
      { label: "Governance", href: "/governance" },
    ],
  },
];

export function AppFooter() {
  return (
    <footer
      className="border-t-2 border-[var(--border-primary)] mt-auto"
      style={{ background: "var(--bg-primary)" }}
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-8">
          {/* Brand Column */}
          <div className="col-span-2 sm:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div
                className="w-6 h-6 border-2 border-[var(--border-primary)] flex items-center justify-center"
                style={{ background: "var(--accent-primary)" }}
              >
                <span className="text-[8px] font-black text-[var(--fg-on-accent)] leading-none">
                  M
                </span>
              </div>
              <span
                className="text-xs font-extrabold tracking-tight uppercase"
                style={{ color: "var(--fg-primary)" }}
              >
                MultiAgent OS
              </span>
            </div>
            <p className="text-body-sm" style={{ color: "var(--fg-tertiary)" }}>
              Orchestrate intelligence.
              <br />
              Deliver impact.
            </p>
          </div>

          {/* Link Columns */}
          {FOOTER_SECTIONS.map((section) => (
            <div key={section.title}>
              <h4
                className="text-h4 mb-3"
                style={{ color: "var(--fg-primary)" }}
              >
                {section.title}
              </h4>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-body-sm transition-colors hover:underline underline-offset-2"
                      style={{ color: "var(--fg-secondary)" }}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div
          className="mt-10 pt-6 border-t border-[var(--border-secondary)] flex flex-col sm:flex-row items-center justify-between gap-4"
        >
          <p className="text-caption" style={{ color: "var(--fg-tertiary)" }}>
            © {new Date().getFullYear()} MultiAgent OS. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <span className="text-caption" style={{ color: "var(--fg-tertiary)" }}>
              Enterprise Multi-Agent AI Platform
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
