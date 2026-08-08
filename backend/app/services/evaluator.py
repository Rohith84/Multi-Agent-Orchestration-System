"""
LLM Agent Evaluator — Automated Quality & Safety Evaluation Engine — Hardened Enterprise Implementation.
"""

from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.aiops import EvaluationReport
from app.schemas.aiops import CreateEvaluationRequest
from app.services.aiops_service import parse_org_id

logger = get_logger(__name__)


class LLMEvaluator:
    """
    Evaluates LLM execution outputs across Accuracy, Completeness, Correctness, Reasoning, Grounding, Hallucination Risk, Code Quality, and Safety.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_agent_output(self, req: CreateEvaluationRequest, raw_org_id: str) -> EvaluationReport:
        """
        Evaluate agent execution and generate structured EvaluationReport under user's organization context.
        """
        org_id = parse_org_id(raw_org_id)

        overall = round(
            (req.accuracy * 0.20)
            + (req.correctness * 0.20)
            + (req.completeness * 0.15)
            + (req.code_quality * 0.15)
            + (req.grounding * 0.15)
            + (req.safety * 0.15)
            - (req.hallucination_risk * 0.5),
            2,
        )
        overall = max(0.0, min(100.0, overall))

        report = EvaluationReport(
            org_id=org_id,
            workflow_run_id=req.workflow_run_id,
            agent_role=req.agent_role,
            accuracy=req.accuracy,
            completeness=req.completeness,
            correctness=req.correctness,
            reasoning=req.reasoning,
            grounding=req.grounding,
            hallucination_risk=req.hallucination_risk,
            citation_quality=req.citation_quality,
            code_quality=req.code_quality,
            safety=req.safety,
            overall_score=overall,
            summary=req.summary,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info("Evaluation report created for workflow '%s' (agent=%s, org_id=%s, overall=%.1f)", req.workflow_run_id, req.agent_role, org_id, overall)
        return report
