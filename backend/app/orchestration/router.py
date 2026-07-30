"""
Agent Router configuration and model router mapping.
"""

from app.core.config import get_settings


def get_model_for_agent(agent_name: str) -> str:
    """
    Get configured model for agent from settings.
    """
    settings = get_settings()
    mapping = {
        "planner": settings.model_planner,
        "research": settings.model_research,
        "coder": settings.model_coder,
        "tester": settings.model_tester,
        "reviewer": settings.model_reviewer,
    }
    return mapping.get(agent_name.lower(), settings.model_name)
