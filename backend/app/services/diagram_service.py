"""
DiagramGeneratorService — Automated Mermaid Architecture & Flow Diagram Generator.

Produces clean Mermaid syntax for Flowcharts, Sequence Diagrams, ERDs, and C4 Architecture models.
"""

from __future__ import annotations

from typing import Any
from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DiagramGeneratorService:
    """
    Generates Mermaid architecture and system flow diagrams.
    """

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()
        self.settings = get_settings()

    async def generate_architecture_diagram(self, user_request: str, plan_text: str, diagram_type: str = "flowchart") -> str:
        """
        Generate a valid Mermaid diagram script based on plan text.
        """
        logger.info("Generating Mermaid architecture diagram (%s)", diagram_type)

        prompt = (
            f"User Request: {user_request}\n\n"
            f"Plan Summary: {plan_text[:1000]}\n\n"
            f"Generate a clean, valid Mermaid.js diagram of type '{diagram_type}'.\n"
            "Return ONLY the valid Mermaid code block enclosed in ```mermaid ... ```."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Enterprise Systems Architect. "
                    "Output ONLY valid Mermaid.js diagram code (flowchart TD, sequenceDiagram, erDiagram, or classDiagram). "
                    "Do NOT include explanations or markdown outside the code block."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            mermaid_code = await self.client.chat(messages, model=self.settings.model_planner)
            return mermaid_code.strip()
        except Exception as e:
            logger.warning("Diagram generation failed: %s. Using default flowchart template.", e)
            return (
                "```mermaid\n"
                "graph TD\n"
                "    User[User Request] --> Planner[Planner Agent]\n"
                "    Planner --> Research[Research & Vision]\n"
                "    Research --> Coder[Coder Agent]\n"
                "    Coder --> Tester[Tester Agent]\n"
                "    Tester --> Reviewer[Reviewer Agent]\n"
                "```"
            )
