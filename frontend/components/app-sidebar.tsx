/**
 * AppSidebar — Shared application sidebar for /app/* routes.
 *
 * Displays grouped navigation sections:
 * - COMMAND CENTER: Dashboard (/app)
 * - AI: AI Assistant (/app/chat), Agents (/app/agents)
 * - AUTOMATION: Workflows (/app/workflows), Builder (/app/workflow-builder)
 * - KNOWLEDGE & TOOLS: Knowledge (/app/knowledge), MCP Tools (/app/tools)
 * - DEVELOPMENT: Workspace (/app/workspace), Artifacts (/app/artifacts)
 * - OBSERVABILITY: Analytics (/app/analytics), Operations (/app/operations)
 * - ENTERPRISE: Governance (/app/governance), Settings (/app/settings)
 *
 * Supports collapsible state, active link styling, hover/focus states, and mobile drawer.
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Bot,
  Layers,
  Workflow,
  FileText,
  Wrench,
  Folder,
  Sparkles,
  BarChart3,
  Activity,
  ShieldCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  X,
  type LucideIcon,
} from "lucide-react";

export interface NavGroup {
  section: string;
  items: {
    label: string;
    href: string;
    icon: LucideIcon;
  }[];
}

export const APP_NAV_GROUPS: NavGroup[] = [
  {
    section: "COMMAND CENTER",
    items: [
      { label: "Dashboard", href: "/app", icon: LayoutDashboard },
    ],
  },
  {
    section: "AI",
    items: [
      { label: "AI Assistant", href: "/app/chat", icon: MessageSquare },
      { label: "Agents", href: "/app/agents", icon: Bot },
    ],
  },
  {
    section: "AUTOMATION",
    items: [
      { label: "Workflows", href: "/app/workflows", icon: Layers },
      { label: "Workflow Builder", href: "/app/workflow-builder", icon: Workflow },
    ],
  },
  {
    section: "KNOWLEDGE & TOOLS",
    items: [
      { label: "Knowledge Base", href: "/app/knowledge", icon: FileText },
      { label: "MCP Tools", href: "/app/tools", icon: Wrench },
    ],
  },
  {
    section: "DEVELOPMENT",
    items: [
      { label: "Workspace Studio", href: "/app/workspace", icon: Folder },
      { label: "Artifact Studio", href: "/app/artifacts", icon: Sparkles },
    ],
  },
  {
    section: "OBSERVABILITY",
    items: [
      { label: "Analytics & LLMOps", href: "/app/analytics", icon: BarChart3 },
      { label: "AI Operations", href: "/app/operations", icon: Activity },
    ],
  },
  {
    section: "ENTERPRISE",
    items: [
      { label: "Governance", href: "/app/governance", icon: ShieldCheck },
      { label: "Settings", href: "/app/settings", icon: Settings },
    ],
  },
];

interface AppSidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function AppSidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen = false,
  onCloseMobile,
}: AppSidebarProps) {
  const pathname = usePathname();

  const isLinkActive = (href: string) => {
    if (href === "/app") return pathname === "/app";
    return pathname.startsWith(href);
  };

  const navContent = (
    <div className="flex flex-col h-full">
      {/* Sidebar Header — Brand */}
      <div className="h-14 px-4 border-b-2 border-[var(--border-primary)] flex items-center justify-between shrink-0"
           style={{ background: "var(--bg-primary)" }}>
        <Link href="/app" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 border-2 border-[var(--border-primary)] flex items-center justify-center shrink-0"
               style={{ background: "var(--accent-primary)" }}>
            <span className="text-[10px] font-black text-[var(--fg-on-accent)] leading-none">M</span>
          </div>
          {!collapsed && (
            <span className="text-xs font-extrabold tracking-tight uppercase truncate"
                  style={{ color: "var(--fg-primary)" }}>
              MultiAgent OS
            </span>
          )}
        </Link>

        {/* Collapse button (desktop) */}
        <button
          onClick={onToggleCollapse}
          className="hidden md:flex w-6 h-6 items-center justify-center border-2 border-[var(--border-primary)] text-[var(--fg-secondary)] hover:text-[var(--fg-primary)] transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        </button>

        {/* Close button (mobile) */}
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="md:hidden w-6 h-6 flex items-center justify-center text-[var(--fg-secondary)]"
            aria-label="Close menu"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Navigation Groups */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {APP_NAV_GROUPS.map((group) => (
          <div key={group.section}>
            {!collapsed && (
              <h4 className="px-2 mb-2 text-[10px] font-bold tracking-wider uppercase text-[var(--fg-tertiary)]">
                {group.section}
              </h4>
            )}
            <ul className="space-y-1">
              {group.items.map((item) => {
                const active = isLinkActive(item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onCloseMobile}
                      className={`
                        flex items-center gap-3 px-2.5 py-2 text-xs font-bold transition-all border-2
                        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-secondary)]
                        ${active
                          ? "border-[var(--border-primary)] text-[var(--fg-on-accent)] bg-[var(--accent-primary)] shadow-[2px_2px_0px_0px_#111111]"
                          : "border-transparent text-[var(--fg-secondary)] hover:text-[var(--fg-primary)] hover:border-[var(--border-secondary)] hover:bg-[var(--bg-secondary)]"
                        }
                      `}
                      title={collapsed ? item.label : undefined}
                    >
                      <item.icon className="w-4 h-4 shrink-0" />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      {/* Sidebar Footer Indicator */}
      {!collapsed && (
        <div className="p-3 border-t-2 border-[var(--border-primary)] shrink-0"
             style={{ background: "var(--bg-secondary)" }}>
          <div className="flex items-center gap-2">
            <div className="status-dot status-dot-online" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--fg-secondary)]">
              5 Agents Ready
            </span>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={`
          hidden md:block border-r-2 border-[var(--border-primary)] shrink-0 transition-all duration-200
          ${collapsed ? "w-16" : "w-60"}
        `}
        style={{ background: "var(--bg-surface)" }}
      >
        {navContent}
      </aside>

      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden animate-fade-in"
          onClick={onCloseMobile}
        />
      )}

      {/* Mobile Drawer */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-64 border-r-2 border-[var(--border-primary)] md:hidden transition-transform duration-200
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        style={{ background: "var(--bg-surface)" }}
      >
        {navContent}
      </aside>
    </>
  );
}
