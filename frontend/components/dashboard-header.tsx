/**
 * DashboardHeader — title bar for the dashboard.
 *
 * Displays the system name with a gradient effect
 * and a subtle animated indicator.
 */

"use client";

import { Activity } from "lucide-react";

export function DashboardHeader() {
  return (
    <div className="mb-10">
      {/* Top accent line */}
      <div className="h-1 w-full bg-gradient-to-r from-violet-600 via-blue-500 to-emerald-500 rounded-full mb-8" />

      <div className="flex items-center gap-4">
        {/* Animated pulse indicator */}
        <div className="relative">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <Activity className="h-6 w-6 text-white" />
          </div>
          <div className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-emerald-400 animate-pulse" />
        </div>

        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight sm:text-3xl">
            Multi Agent Orchestration System
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            System health &amp; status dashboard
          </p>
        </div>
      </div>

      {/* Divider */}
      <div className="mt-6 h-px bg-gradient-to-r from-zinc-800 via-zinc-700 to-zinc-800" />
    </div>
  );
}
