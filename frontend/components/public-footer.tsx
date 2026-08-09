/**
 * PublicFooter — Professional enterprise footer for public MultiAgent OS pages.
 *
 * Used on /, /login, /signup.
 * Separate from existing AppFooter.
 */

"use client";

import Link from "next/link";

const FOOTER_SECTIONS = [
  {
    title: "Product",
    links: [
      { label: "How It Works", href: "#architecture" },
      { label: "Agents", href: "#agents" },
      { label: "Capabilities", href: "#platform" },
      { label: "Enterprise", href: "#governance" },
    ],
  },
  {
    title: "Platform",
    links: [
      { label: "Workflows", href: "/app/workflows" },
      { label: "Knowledge", href: "/app/knowledge" },
      { label: "Tools", href: "/app/tools" },
      { label: "Analytics", href: "/app/analytics" },
      { label: "Governance", href: "/app/governance" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Sign In", href: "/login" },
      { label: "Launch OS", href: "/app" },
    ],
  },
];

export function PublicFooter() {
  const handleAnchorClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.startsWith("#")) {
      e.preventDefault();
      const el = document.getElementById(href.slice(1));
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  };

  return (
    <footer
      className="border-t-2 border-[var(--border-primary)]"
      style={{ background: "var(--bg-primary)" }}
      role="contentinfo"
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
              Enterprise multi-agent
              <br />
              orchestration platform.
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
                  <li key={link.label}>
                    {link.href.startsWith("#") ? (
                      <a
                        href={link.href}
                        onClick={(e) => handleAnchorClick(e, link.href)}
                        className="text-body-sm transition-colors hover:underline underline-offset-2"
                        style={{ color: "var(--fg-secondary)" }}
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="text-body-sm transition-colors hover:underline underline-offset-2"
                        style={{ color: "var(--fg-secondary)" }}
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="mt-10 pt-6 border-t border-[var(--border-secondary)] flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-caption" style={{ color: "var(--fg-tertiary)" }}>
            © {new Date().getFullYear()} MultiAgent OS
          </p>
          <span className="text-caption" style={{ color: "var(--fg-tertiary)" }}>
            Enterprise Multi-Agent AI Platform
          </span>
        </div>
      </div>
    </footer>
  );
}
