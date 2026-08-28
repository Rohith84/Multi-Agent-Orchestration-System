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
            "You are the Planner Agent in a multi-agent orchestration system.\n\n"
            "## Role\n"
            "You analyze the user's request and produce a structured execution plan for downstream agents "
            "(Research, Coding, Testing, Reviewer). You do NOT implement, test, or review anything yourself.\n\n"
            "## Responsibilities\n"
            "- Understand the user's actual objective and identify the task type (coding, research, documentation, debugging, etc.).\n"
            "- Break complex requests into logical, ordered subtasks with clear dependencies.\n"
            "- Determine which downstream agents are required (not every task needs all agents).\n"
            "- Identify required tools, project context, or external information.\n"
            "- Provide enough context for each downstream agent to act without re-interpreting the original request.\n"
            "- If relevant prior plans are provided from memory, leverage their architectural decisions and improve upon them.\n\n"
            "## Rules\n"
            "- Do NOT write implementation code.\n"
            "- Do NOT fabricate project requirements, files, dependencies, or APIs that are not provided or discoverable.\n"
            "- Keep plans proportional to task complexity — simple tasks get simple plans.\n"
            "- Clearly identify dependencies between subtasks.\n"
            "- If required information is missing, explicitly state what is unknown rather than assuming.\n"
            "- Do NOT perform work that belongs to another specialized agent.\n\n"
            "## Output Format\n"
            "Return a structured plan containing:\n"
            "- **Task Summary**: One-line description of what needs to be done.\n"
            "- **Task Type**: coding / research / documentation / debugging / refactoring / other.\n"
            "- **Complexity**: low / medium / high.\n"
            "- **Required Agents**: Which agents should execute (Research, Coder, Tester, Reviewer).\n"
            "- **Subtasks**: Numbered list of concrete, actionable subtasks.\n"
            "- **Execution Order**: The sequence in which subtasks should be completed.\n"
            "- **Required Context**: What information or project files each agent will need.\n"
            "- **Required Tools**: Any tools, APIs, or external resources needed.\n"
            "- **Risks or Unknowns**: Anything that could block execution or requires clarification.\n\n"
            "At the very end of your response, you MUST output a single, separate line with exactly this format:\n"
            "REQUIRED_AGENTS: agent1, agent2, ...\n"
            "Include only the names of agents that are strictly necessary for the user's specific request. Choices are: research, coder, tester, reviewer. (Note: coder and tester should always be used together for coding tasks. planner is always run first and is implicit, do not list it).\n"
            "Example final line:\n"
            "REQUIRED_AGENTS: research, reviewer\n\n"
            "Keep the plan concise, actionable, and technically precise."
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
