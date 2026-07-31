"""
Workflow Builder, Custom Agents, Graph Validation & Simulation API Endpoints.

Provides:
- GET /api/workflows/templates                  — list workflow templates
- POST /api/workflows/templates                 — create custom workflow template
- GET /api/workflows/builder/{id}               — fetch template details
- POST /api/workflows/builder/{id}/simulate     — dry-run simulation
- POST /api/workflows/builder/{id}/execute      — execute dynamic workflow graph
- GET /api/custom-agents                        — list custom agents
- POST /api/custom-agents                       — create custom agent definition
"""

from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.schemas.workflow_builder import (
    WorkflowTemplateSchema,
    CustomAgentSchema,
    CreateWorkflowTemplateRequest,
    CreateCustomAgentRequest,
    ValidationReportSchema,
    SimulationReportSchema,
)
from app.services.workflow_builder_service import WorkflowBuilderService
from app.orchestration.dynamic_graph import DynamicGraphCompiler

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["workflow-builder"])


@router.get("/workflows/templates", response_model=list[WorkflowTemplateSchema])
async def list_workflow_templates(
    db: AsyncSession = Depends(get_db),
) -> list[WorkflowTemplateSchema]:
    """List all preset and custom workflow templates."""
    service = WorkflowBuilderService(db)
    return await service.list_templates()


@router.post("/workflows/templates", response_model=WorkflowTemplateSchema)
async def create_workflow_template(
    request: CreateWorkflowTemplateRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowTemplateSchema:
    """Create a new custom workflow template."""
    service = WorkflowBuilderService(db)
    try:
        return await service.create_template(
            name=request.name,
            description=request.description,
            graph_json=request.graph_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workflows/builder/{template_id}", response_model=WorkflowTemplateSchema)
async def get_workflow_template_details(
    template_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkflowTemplateSchema:
    """Fetch details for a specific workflow template."""
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    service = WorkflowBuilderService(db)
    try:
        return await service.get_template(tid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/workflows/builder/{template_id}/simulate", response_model=SimulationReportSchema)
async def simulate_workflow_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
) -> SimulationReportSchema:
    """Dry-run simulation of workflow template execution without calling LLMs."""
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    service = WorkflowBuilderService(db)
    tmpl = await service.get_template(tid)
    return service.simulate_graph(tmpl.graph_json)


@router.post("/workflows/builder/{template_id}/execute")
async def execute_dynamic_workflow(
    template_id: str,
    user_request: str = "Generate a sample project",
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute dynamic workflow graph compiled from template JSON."""
    try:
        tid = uuid.UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid template ID format")

    service = WorkflowBuilderService(db)
    tmpl = await service.get_template(tid)

    compiler = DynamicGraphCompiler()
    compiled_graph = compiler.compile(tmpl.graph_json)

    initial_state = {
        "session_id": str(uuid.uuid4()),
        "user_request": user_request,
        "current_node": "start",
        "node_outputs": {},
        "execution_history": [],
    }

    final_state = await compiled_graph.ainvoke(initial_state)

    return {
        "status": "completed",
        "template_name": tmpl.name,
        "nodes_executed": final_state.get("execution_history", []),
        "outputs": final_state.get("node_outputs", {}),
    }


@router.get("/custom-agents", response_model=list[CustomAgentSchema])
async def list_custom_agents(
    db: AsyncSession = Depends(get_db),
) -> list[CustomAgentSchema]:
    """List all custom agent definitions."""
    service = WorkflowBuilderService(db)
    return await service.list_custom_agents()


@router.post("/custom-agents", response_model=CustomAgentSchema)
async def create_custom_agent(
    request: CreateCustomAgentRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomAgentSchema:
    """Create a user-defined custom agent."""
    service = WorkflowBuilderService(db)
    return await service.create_custom_agent(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        llm_model=request.llm_model,
        temperature=request.temperature,
        allowed_mcp_tools=request.allowed_mcp_tools,
    )
