"""
Planner Agent.
Decomposes user request into structured execution plans.
Queries Planning Memory vector store to reuse past architectural plans and inspects project structure via MCP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.vectorstore.planning_memory import PlanningMemoryStore

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class PlannerAgent:
    """
    Planner Agent is responsible for analyzing requirements, planning execution steps,
    reusing prior architectural plans from memory, and outputting a clear task decomposition list.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_planner
        self.memory_store = PlanningMemoryStore()

    async def execute(
        self,
        user_request: str,
        history: list[dict[str, str]] | None = None,
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        logger.info("Executing Planner Agent with model=%s", self.model)

        # 1. Retrieve similar past plans from Planning Memory
        memory_context = ""
        try:
            similar_plans = await self.memory_store.search_similar_plans(user_request, top_k=2)
            if similar_plans:
                plan_snippets = []
                for idx, p in enumerate(similar_plans):
                    plan_snippets.append(
                        f"--- Prior Similar Goal (Similarity: {p['similarity_score']}) ---\n"
                        f"Goal: {p['goal']}\nPlan Snippet:\n{p['plan'][:400]}..."
                    )
                memory_context = f"\n\nReused Planning Memories:\n" + "\n\n".join(plan_snippets)
        except Exception as e:
            logger.debug("Planner memory search skipped: %s", e)

        # 2. MCP Tool: Inspect project structure for context
        project_context = ""
        if tool_runner:
            try:
                result = await tool_runner.run_tool(
                    "filesystem.list_directory",
                    {"path": "backend/app"},
                )
                if result:
                    entries = result.get("entries", [])
                    listing = "\n".join(
                        f"  {'[DIR]' if e['type'] == 'directory' else '[FILE]'} {e['name']}"
                        for e in entries
                    )
                    project_context = f"\n\nProject Structure (backend/app):\n{listing}"
            except Exception as e:
                logger.debug("Planner MCP tool failed (non-critical): %s", e)

        system_prompt = (
            "You are the Planner Agent. Your job is to understand the user's software/system request "
            "and create a clear, step-by-step task decomposition and planning output.\n"
            "If relevant prior plans are provided from memory, leverage their architectural decisions and improve upon them.\n\n"
            "Outline:\n"
            "1. Objective\n"
            "2. Required Components / Structure\n"
            "3. Step-by-Step Task Breakdown\n"
            "Keep the output structured and technical. Do not write the code itself, focus only on the plan."
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if history:
            messages.extend(history)

        prompt = f"Please plan the execution for this request:\n\n{user_request}"
        if memory_context:
            prompt += memory_context
        if project_context:
            prompt += project_context

        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat(messages, model=self.model)
        return response
