"""
Prompt Registry API Endpoints.

Provides:
- GET /api/prompts — list all versioned prompt templates
- POST /api/prompts — create a new prompt version for an agent
- POST /api/prompts/{id}/activate — set a prompt version as active
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.schemas.analytics import PromptVersionSchema, PromptCreateRequest
from app.services.prompt_registry import PromptRegistryService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def _get_prompt_service(db: AsyncSession = Depends(get_db)) -> PromptRegistryService:
    return PromptRegistryService(db)


@router.get("", response_model=list[PromptVersionSchema])
async def list_prompts(
    service: PromptRegistryService = Depends(_get_prompt_service),
) -> list[PromptVersionSchema]:
    """List all prompt versions in the registry."""
    return await service.list_prompts()


@router.post("", response_model=PromptVersionSchema)
async def create_prompt(
    request: PromptCreateRequest,
    service: PromptRegistryService = Depends(_get_prompt_service),
) -> PromptVersionSchema:
    """Create a new prompt version for an agent and activate it."""
    return await service.create_prompt_version(
        agent_name=request.agent_name,
        version=request.version,
        template=request.template,
        description=request.description,
    )


@router.post("/{prompt_id}/activate", response_model=PromptVersionSchema)
async def activate_prompt(
    prompt_id: str,
    service: PromptRegistryService = Depends(_get_prompt_service),
) -> PromptVersionSchema:
    """Activate a specific prompt version by ID."""
    try:
        pid = uuid.UUID(prompt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid prompt ID format")

    try:
        return await service.activate_prompt_version(pid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
