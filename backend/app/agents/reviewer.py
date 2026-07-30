"""
Reviewer Agent.
Reviews final code, checks architectural patterns, and scores the quality.
"""

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReviewerAgent:
    """
    Reviewer Agent reviews the whole process outputs, checks SOLID/security rules,
    and returns a summary + quality score.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_reviewer

    async def execute(
        self,
        user_request: str,
        execution_plan: str,
        generated_code: str,
        test_results: str,
    ) -> str:
        logger.info("Executing Reviewer Agent with model=%s", self.model)

        system_prompt = (
            "You are the Reviewer Agent. Your job is to review the user's initial request, "
            "the plan, the generated code, and the test results. Perform a full review of architecture, "
            "security, readability, and SOLID principles. Deliver a structured audit checklist and an overall "
            "quality score out of 100.\n\n"
            "Outline:\n"
            "1. Architectural & SOLID Compliance\n"
            "2. Readability & Maintainability Audit\n"
            "3. Security Check\n"
            "4. Final Quality Score (e.g. Quality Score: 95/100)\n"
            "5. Brief Summary Response for the user"
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Generated Code:\n{generated_code}\n\n"
            f"Test Results:\n{test_results}\n\n"
            f"Please conduct the final review, provide the scoring, and write a summary response."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat(messages, model=self.model)
        return response
