"""
Tester Agent.
Detects bugs, verifies syntax, and generates unit test configurations.
"""

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TesterAgent:
    """
    Tester Agent analyzes generated code for security/syntax flaws and generates unit tests.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_tester

    async def execute(self, generated_code: str, execution_plan: str) -> str:
        logger.info("Executing Tester Agent with model=%s", self.model)

        system_prompt = (
            "You are the Tester Agent. Your job is to analyze the generated code for syntax, logic errors, "
            "and security issues, suggest fixes, and generate unit tests (e.g. pytest or equivalent).\n\n"
            "Outline:\n"
            "1. Code Quality & Bug Analysis\n"
            "2. Suggested Fixes / Code Improvements\n"
            "3. Complete Unit Tests (with assert checks)"
        )

        prompt = (
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Generated Code:\n{generated_code}\n\n"
            f"Please test this implementation and provide quality feedback and unit test scripts."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat(messages, model=self.model)
        return response
