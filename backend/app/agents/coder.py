"""
Coder Agent.
Synthesizes source code following the execution plan and research guidelines.
"""

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoderAgent:
    """
    Coder Agent outputs the actual software implementation (code scripts, structures).
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_coder

    async def execute(self, user_request: str, execution_plan: str, research_notes: str) -> str:
        logger.info("Executing Coder Agent with model=%s", self.model)

        system_prompt = (
            "You are the Coder Agent. Your job is to output clean, well-structured, production-ready source code "
            "based on the user request, the plan, and the research notes provided.\n\n"
            "Include inline comments and docstrings. Provide the complete code blocks without placeholders. "
            "Ensure you address code structure and correct syntax."
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Research Notes:\n{research_notes}\n\n"
            f"Please generate the complete source code implementation."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat(messages, model=self.model)
        return response
