"""
Research Agent.
Searches context, summarizes documentation, and prepares research context.
"""

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResearchAgent:
    """
    Research Agent gathers background info and documentation hints relevant to the generated plan.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_research

    async def execute(self, user_request: str, execution_plan: str) -> str:
        logger.info("Executing Research Agent with model=%s", self.model)

        system_prompt = (
            "You are the Research Agent. Your job is to research best practices, dependencies, "
            "and architectural specifications required for the proposed plan. Provide solid implementation guidelines, "
            "API signatures, or security considerations that the Coder Agent must follow.\n\n"
            "Outline:\n"
            "1. Architectural Principles / Best Practices\n"
            "2. Critical Dependencies & API Reference Guidelines\n"
            "3. Security & Context Checklists"
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Proposed Execution Plan:\n{execution_plan}\n\n"
            f"Please conduct research and provide notes for this plan."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat(messages, model=self.model)
        return response
