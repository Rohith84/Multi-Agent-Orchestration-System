"""
Prompt Registry Service.

Manages versioned agent system prompts stored in PostgreSQL.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.metrics import PromptVersion
from app.schemas.analytics import PromptVersionSchema

logger = get_logger(__name__)

# Default prompts fallback map
DEFAULT_AGENT_PROMPTS = {
    "planner": (
        "You are the Planner Agent. Your job is to understand the user's software/system request "
        "and create a clear, step-by-step task decomposition and planning output.\n"
        "Outline:\n1. Objective\n2. Required Components / Structure\n3. Step-by-Step Task Breakdown"
    ),
    "research": (
        "You are the Research Agent. Your job is to research best practices, dependencies, "
        "and architectural specifications required for the proposed plan using Knowledge Base context."
    ),
    "coder": (
        "You are the Coder Agent. Your job is to output clean, well-structured, production-ready source code "
        "based on the user request, plan, and research notes."
    ),
    "tester": (
        "You are the Tester Agent. Your job is to analyze generated code for syntax, logic errors, "
        "and security issues, suggest fixes, and generate unit tests."
    ),
    "reviewer": (
        "You are the Reviewer Agent. Your job is to perform a full review of architecture, security, "
        "readability, and SOLID compliance, deliver a checklist, citations list, and quality score."
    ),
}


class PromptRegistryService:
    """
    Manages creation, lookup, and activation of prompt versions.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_prompt(self, agent_name: str) -> str:
        """Retrieve the currently active prompt template for an agent."""
        result = await self.db.execute(
            select(PromptVersion)
            .where(PromptVersion.agent_name == agent_name, PromptVersion.active == True)
            .order_by(PromptVersion.created_at.desc())
            .limit(1)
        )
        pv = result.scalar_one_or_none()
        if pv:
            return pv.template
        return DEFAULT_AGENT_PROMPTS.get(agent_name, "You are a helpful AI Agent.")

    async def list_prompts(self) -> list[PromptVersionSchema]:
        """List all registered prompt versions."""
        result = await self.db.execute(
            select(PromptVersion).order_by(PromptVersion.created_at.desc())
        )
        pvs = result.scalars().all()
        return [PromptVersionSchema.model_validate(p) for p in pvs]

    async def create_prompt_version(
        self,
        agent_name: str,
        version: str,
        template: str,
        description: str = "",
    ) -> PromptVersionSchema:
        """Create a new prompt version and activate it."""
        # Deactivate older active prompts for this agent
        await self.db.execute(
            update(PromptVersion)
            .where(PromptVersion.agent_name == agent_name)
            .values(active=False)
        )

        pv = PromptVersion(
            agent_name=agent_name,
            version=version,
            template=template,
            description=description,
            active=True,
        )
        self.db.add(pv)
        await self.db.commit()

        logger.info("Created and activated prompt %s %s", agent_name, version)
        return PromptVersionSchema.model_validate(pv)

    async def activate_prompt_version(self, prompt_id: uuid.UUID) -> PromptVersionSchema:
        """Activate a specific prompt version by ID."""
        result = await self.db.execute(
            select(PromptVersion).where(PromptVersion.id == prompt_id)
        )
        pv = result.scalar_one_or_none()
        if not pv:
            raise ValueError(f"Prompt version {prompt_id} not found")

        await self.db.execute(
            update(PromptVersion)
            .where(PromptVersion.agent_name == pv.agent_name)
            .values(active=False)
        )
        pv.active = True
        await self.db.commit()

        return PromptVersionSchema.model_validate(pv)
