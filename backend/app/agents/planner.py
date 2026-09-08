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
from app.schemas.contracts import PlanContract
from app.schemas.reasoning import ReasoningMetadata
from app.orchestration.plan_validator import PlanContractValidator, PlanValidationResult

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class PlannerResult:
    """Structured result returned by PlannerAgent."""

    def __init__(
        self,
        raw_output: str,
        is_valid: bool,
        contract: PlanContract | None = None,
        errors: list[str] | None = None,
        reasoning_metadata: ReasoningMetadata | None = None,
    ) -> None:
        self.raw_output = raw_output
        self.is_valid = is_valid
        self.contract = contract
        self.errors = errors or []
        self.reasoning_metadata = reasoning_metadata
        if contract:
            self.formatted_plan = contract.to_markdown()
        else:
            err_text = "; ".join(self.errors) if self.errors else "Unknown validation error"
            self.formatted_plan = (
                f"### Plan Validation Error (Rejected by Plan Contract)\n"
                f"{err_text}\n\n"
                f"Original Output:\n{raw_output}"
            )


class PlannerAgent:
    """
    Planner Agent is responsible for analyzing requirements, planning execution steps,
    reusing prior architectural plans from memory, and outputting a validated PlanContract.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_planner
        self.memory_store = PlanningMemoryStore()

    async def execute_contract(
        self,
        user_request: str,
        history: list[dict[str, str]] | None = None,
        tool_runner: MCPToolRunner | None = None,
    ) -> PlannerResult:
        """
        Execute planner and return a validated PlannerResult with PlanContract.
        """
        logger.info("Executing Planner Agent with model=%s", self.model)

        # 1. Retrieve similar past plans from Planning Memory
        memory_context = ""
        try:
            similar_plans = await self.memory_store.search_similar_plans(user_request, top_k=2)
            if similar_plans:
                plan_snippets = []
                for p in similar_plans:
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
            "## Role & Responsibilities\n"
            "Analyze the user request, evaluate architectural requirements, and generate a structured execution plan conforming to the PlanContract schema.\n"
            "Do NOT write implementation code, test execution scripts, or final review output.\n\n"
            "## Reasoning & Quality Guidelines\n"
            "- Understand the user's objective before decomposing it into subtasks.\n"
            "- Consider existing project architecture and prior memories as contextual evidence rather than strict templates.\n"
            "- Keep plans proportional to task complexity — avoid over-decomposition or redundant subtasks.\n"
            "- Ensure logical dependency ordering between Research, Coder, Tester, and Reviewer.\n"
            "- Clearly identify potential risks, unknowns, or trade-offs in the design.\n\n"
            "## Requirements\n"
            "- Subtasks: You MUST provide strictly between 3 and 6 discrete, non-duplicate subtasks.\n"
            "- Allowed agents: 'research', 'coder', 'tester', 'reviewer'.\n"
            "- For coding/building tasks, include 'research', 'coder', 'tester', 'reviewer'.\n"
            "- Every subtask MUST have a unique 'id', assigned 'agent', concrete 'description', and 'dependencies' array.\n"
            "- Include 'file_manifest' listing all files to create.\n"
            "- Include 'acceptance_criteria' with concrete testable criteria.\n\n"
            "## Output Format (JSON)\n"
            "Return valid JSON matching this schema:\n"
            "```json\n"
            "{\n"
            '  "task_summary": "One-line task summary",\n'
            '  "task_type": "coding",\n'
            '  "complexity": "medium",\n'
            '  "required_agents": ["research", "coder", "tester", "reviewer"],\n'
            '  "subtasks": [\n'
            '    {"id": 1, "agent": "research", "description": "Research requirements and specs", "dependencies": []},\n'
            '    {"id": 2, "agent": "coder", "description": "Implement core logic and modules", "dependencies": [1]},\n'
            '    {"id": 3, "agent": "tester", "description": "Create and run unit test suite", "dependencies": [2]},\n'
            '    {"id": 4, "agent": "reviewer", "description": "Review quality and architectural evidence", "dependencies": [3]}\n'
            "  ],\n"
            '  "file_manifest": ["app/main.py", "tests/test_main.py"],\n'
            '  "acceptance_criteria": ["All tests pass cleanly", "No linter errors"],\n'
            '  "reasoning": {\n'
            '    "decision": "Chosen workflow architecture",\n'
            '    "evidence_used": ["Project structure", "User requirements"],\n'
            '    "rationale": "Why this decomposition fits task complexity",\n'
            '    "alternatives_considered": ["Single monolithic task"],\n'
            '    "trade_offs": ["Modular separation vs generation overhead"],\n'
            '    "risks": ["Potential API contract mismatches"]\n'
            '  }\n'
            "}\n"
            "```\n"
            "Strict rule: Never generate more than 6 subtasks. Never duplicate subtasks."
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if history:
            messages.extend(history)

        prompt = f"Please generate a structured PlanContract for this request:\n\n{user_request}"
        if memory_context:
            prompt += memory_context
        if project_context:
            prompt += project_context

        messages.append({"role": "user", "content": prompt})

        raw_response = await self.client.chat(messages, model=self.model, max_tokens=1400)

        # 3. Deterministic Plan Contract Validation
        val_result: PlanValidationResult = PlanContractValidator.validate(raw_response)

        # Extract non-authoritative reasoning metadata if available
        reasoning_meta: ReasoningMetadata | None = None
        try:
            import json, re
            match = re.search(r"```json\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
            json_str = match.group(1) if match else raw_response
            data = json.loads(json_str)
            if isinstance(data, dict) and "reasoning" in data and isinstance(data["reasoning"], dict):
                reasoning_meta = ReasoningMetadata(**data["reasoning"])
            elif isinstance(data, dict):
                reasoning_meta = ReasoningMetadata(
                    decision=data.get("task_summary", ""),
                    evidence_used=["User Request"],
                    rationale=f"Task decomposed into {len(data.get('subtasks', []))} subtasks.",
                    risks=[],
                )
        except Exception:
            reasoning_meta = None

        return PlannerResult(
            raw_output=raw_response,
            is_valid=val_result.is_valid,
            contract=val_result.contract,
            errors=val_result.errors,
            reasoning_metadata=reasoning_meta,
        )

    async def execute(
        self,
        user_request: str,
        history: list[dict[str, str]] | None = None,
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        """
        Main execution endpoint for PlannerAgent.
        Returns the validated formatted plan string or the rejection summary.
        """
        result = await self.execute_contract(
            user_request=user_request,
            history=history,
            tool_runner=tool_runner,
        )
        return result.formatted_plan
