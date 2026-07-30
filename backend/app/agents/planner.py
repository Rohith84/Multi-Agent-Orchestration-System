"""
Planner Agent.
Decomposes user request into structured execution plans.
"""

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PlannerAgent:
    """
    Planner Agent is responsible for analyzing requirements, planning execution steps,
    and outputting a clear task decomposition list.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_planner

    async def execute(self, user_request: str, history: list[dict[str, str]] | None = None) -> str:
        logger.info("Executing Planner Agent with model=%s", self.model)

        system_prompt = (
            "You are the Planner Agent. Your job is to understand the user's software/system request "
            "and create a clear, step-by-step task decomposition and planning output.\n\n"
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

        messages.append({
            "role": "user",
            "content": f"Please plan the execution for this request:\n\n{user_request}"
        })

        response = await self.client.chat(messages, model=self.model)
        return response
