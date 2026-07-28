/**
 * StatusCard — reusable component for displaying subsystem status.
 *
 * Supports 4 states: connected, disconnected, loading, placeholder.
 * Will be reused for agent status cards in future milestones.
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CheckCircle2,
  XCircle,
  Circle,
  Loader2,
  type LucideIcon,
} from "lucide-react";

export type StatusType = "connected" | "disconnected" | "loading" | "placeholder";

interface StatusCardProps {
  /** Display title (e.g., "Backend Status") */
  title: string;
  /** Current status */
  status: StatusType;
  /** Descriptive message */
  message: string;
  /** Optional custom icon */
  icon?: LucideIcon;
  /** Unique ID for testing */
  id?: string;
}

const statusConfig: Record<
  StatusType,
  { color: string; bgColor: string; borderColor: string; badgeText: string; Icon: LucideIcon }
> = {
  connected: {
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/20",
    badgeText: "Connected",
    Icon: CheckCircle2,
  },
  disconnected: {
    color: "text-red-400",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/20",
    badgeText: "Disconnected",
    Icon: XCircle,
  },
  loading: {
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/20",
    badgeText: "Checking...",
    Icon: Loader2,
  },
  placeholder: {
    color: "text-zinc-500",
    bgColor: "bg-zinc-500/10",
    borderColor: "border-zinc-500/20",
    badgeText: "Pending",
    Icon: Circle,
  },
};

export function StatusCard({ title, status, message, icon, id }: StatusCardProps) {
  const config = statusConfig[status];
  const DisplayIcon = icon || config.Icon;

  if (status === "loading") {
    return (
      <Card
        id={id}
        className="border-zinc-800 bg-zinc-900/50 backdrop-blur-sm"
      >
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-32 bg-zinc-800" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-10 w-10 rounded-full bg-zinc-800" />
          <Skeleton className="h-4 w-48 bg-zinc-800" />
          <Skeleton className="h-6 w-20 bg-zinc-800" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      id={id}
      className={`
        border transition-all duration-300 hover:scale-[1.02]
        ${config.borderColor} ${config.bgColor}
        bg-zinc-900/50 backdrop-blur-sm
      `}
    >
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-zinc-400">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className={`${config.color}`}>
          <DisplayIcon className="h-10 w-10" />
        </div>
        <p className="text-sm text-zinc-300">{message}</p>
        <Badge
          variant="outline"
          className={`${config.color} ${config.borderColor} text-xs`}
        >
          {config.badgeText}
        </Badge>
      </CardContent>
    </Card>
  );
}
