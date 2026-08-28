"""
AnalyticsService — Business logic layer for observability, LLMOps metrics, model comparison, and exports.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.metrics import AgentMetric, WorkflowMetric
from app.models.workflow import Workflow, WorkflowCheckpoint, WorkflowApproval
from app.models.tool_execution import ToolExecution
from app.models.workspace import QualityReport
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    ModelPerformanceStats,
    ToolPerformanceStats,
    RAGPerformanceStats,
    AgentMetricSchema,
    WorkflowMetricSchema,
)

logger = get_logger(__name__)


class AnalyticsService:
    """
    Computes system observability metrics, model comparisons, tool performance, and export reports.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dashboard_analytics(self) -> DashboardAnalyticsResponse:
        """Compute aggregated dashboard analytics across all workflows, models, and tools."""
        # 1. Total workflows and average latency
        wf_count_res = await self.db.execute(select(func.count(Workflow.id)))
        total_workflows = wf_count_res.scalar() or 0

        avg_lat_res = await self.db.execute(
            select(func.avg(Workflow.execution_time)).where(Workflow.status == "completed")
        )
        avg_wf_latency = avg_lat_res.scalar()
        if avg_wf_latency is not None:
            avg_wf_latency = round(float(avg_wf_latency), 2)

        # 2. Total tokens and overall score
        total_tokens = None  # Token usage not tracked by provider integrations

        avg_score_res = await self.db.execute(select(func.avg(QualityReport.overall_score)))
        overall_score = avg_score_res.scalar()
        if overall_score is not None:
            overall_score = round(float(overall_score), 1)

        # 3. Success rate
        success_wf_res = await self.db.execute(
            select(func.count(Workflow.id)).where(Workflow.status == "completed")
        )
        success_count = success_wf_res.scalar() or 0

        failed_wf_res = await self.db.execute(
            select(func.count(Workflow.id)).where(Workflow.status == "failed")
        )
        failed_count = failed_wf_res.scalar() or 0

        total_completed_or_failed = success_count + failed_count
        if total_completed_or_failed > 0:
            success_rate = round((success_count / total_completed_or_failed) * 100, 1)
        else:
            success_rate = None

        # 4. Model stats comparison
        model_stats = await self._compute_model_stats()

        # 5. Tool performance stats
        tool_stats = await self._compute_tool_stats()

        # 6. RAG retrieval stats
        rag_stats = await self._compute_rag_stats()

        # 7. Recent agent metrics
        recent_res = await self.db.execute(
            select(AgentMetric).order_by(AgentMetric.created_at.desc()).limit(10)
        )
        recent_metrics = [AgentMetricSchema.model_validate(m) for m in recent_res.scalars().all()]

        return DashboardAnalyticsResponse(
            overall_quality_score=overall_score,
            total_workflows_executed=total_workflows,
            total_tokens_consumed=total_tokens,
            avg_workflow_latency=avg_wf_latency,
            success_rate_percentage=success_rate,
            model_stats=model_stats,
            tool_stats=tool_stats,
            rag_stats=rag_stats,
            recent_agent_metrics=recent_metrics,
            token_usage_available=False,
            rag_metrics_available=False,
        )

    async def export_report(self, format_type: str = "json") -> str:
        """Export workflow metrics report as JSON or CSV string."""
        metrics_res = await self.db.execute(
            select(AgentMetric).order_by(AgentMetric.created_at.desc()).limit(100)
        )
        metrics = metrics_res.scalars().all()

        if format_type.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Metric ID", "Workflow ID", "Agent Name", "Model", "Duration (s)",
                "Total Tokens", "Status", "Score", "Created At"
            ])
            for m in metrics:
                writer.writerow([
                    str(m.id), str(m.workflow_id), m.agent_name, m.model,
                    m.duration, m.total_tokens, m.status, m.score, m.created_at.isoformat()
                ])
            return output.getvalue()
        else:
            export_data = [
                {
                    "id": str(m.id),
                    "workflow_id": str(m.workflow_id),
                    "agent_name": m.agent_name,
                    "model": m.model,
                    "duration": m.duration,
                    "total_tokens": m.total_tokens,
                    "status": m.status,
                    "score": m.score,
                    "eval_breakdown": m.eval_breakdown,
                    "created_at": m.created_at.isoformat(),
                }
                for m in metrics
            ]
            return json.dumps({"report_title": "Multi-Agent Workflow Observability Export", "data": export_data}, indent=2)

    async def _compute_model_stats(self) -> list[ModelPerformanceStats]:
        """Group performance metrics by LLM model."""
        from sqlalchemy import case
        res = await self.db.execute(
            select(
                AgentMetric.model,
                func.count(AgentMetric.id),
                func.avg(AgentMetric.duration),
                func.avg(AgentMetric.total_tokens),
                func.avg(AgentMetric.score),
                func.sum(case((AgentMetric.status == "success", 1), else_=0)),
            ).group_by(AgentMetric.model)
        )
        stats = []
        for row in res.fetchall():
            model_name, count, avg_dur, avg_tok, avg_sc, success_count = row
            success_count = success_count or 0
            success_rate = round((success_count / max(1, count)) * 100, 1)
            stats.append(ModelPerformanceStats(
                model_name=model_name,
                total_calls=count,
                avg_duration=round(avg_dur or 0.0, 2),
                avg_tokens=round(avg_tok or 0.0, 0),
                avg_score=round(avg_sc or 8.5, 1),
                success_rate=success_rate,
            ))
        return stats

    async def _compute_tool_stats(self) -> list[ToolPerformanceStats]:
        """Group performance metrics by MCP tool."""
        from sqlalchemy import case
        res = await self.db.execute(
            select(
                ToolExecution.tool_name,
                func.count(ToolExecution.id),
                func.avg(ToolExecution.execution_time),
                func.sum(case((ToolExecution.status == "success", 1), else_=0)),
            ).group_by(ToolExecution.tool_name)
        )
        stats = []
        for row in res.fetchall():
            t_name, count, avg_dur, success_count = row
            success_count = success_count or 0
            success_rate = round((success_count / max(1, count)) * 100, 1)
            failure_count = count - success_count
            cat = t_name.split(".")[0] if "." in t_name else "general"
            stats.append(ToolPerformanceStats(
                tool_name=t_name,
                category=cat,
                total_calls=count,
                avg_duration=round(avg_dur or 0.0, 3),
                success_rate=success_rate,
                failure_count=failure_count,
            ))
        return stats

    async def _compute_rag_stats(self) -> RAGPerformanceStats | None:
        """Compute RAG retrieval analytics. Returns None as RAG query telemetry is not tracked."""
        return None
