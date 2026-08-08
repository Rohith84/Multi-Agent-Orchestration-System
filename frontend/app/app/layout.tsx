/**
 * Application Shell Layout for /app/* routes.
 *
 * Provides a unified sidebar and topbar surrounding all application pages:
 * - /app (Command Center Dashboard)
 * - /app/chat (AI Assistant)
 * - /app/agents (Agent Control Center)
 * - /app/workflows (Workflows)
 * - /app/workflow-builder (Workflow Builder)
 * - /app/knowledge (Knowledge Base)
 * - /app/tools (MCP Tools)
 * - /app/workspace (Workspace Studio)
 * - /app/artifacts (Artifact Studio)
 * - /app/analytics (Analytics & LLMOps)
 * - /app/operations (AI Operations)
 * - /app/governance (Governance)
 * - /app/settings (Settings)
 */

"use client";

import { useState, type ReactNode } from "react";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";

export default function AppLayout({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden"
         style={{ background: "var(--bg-primary)", color: "var(--fg-primary)" }}>
      {/* Shared Application Sidebar */}
      <AppSidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(!collapsed)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Shared Topbar */}
        <AppTopbar onOpenMobileMenu={() => setMobileOpen(true)} />

        {/* Page Content Container */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
