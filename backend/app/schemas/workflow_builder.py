"""
Pydantic schemas for Workflow Templates, Custom Agents, Graph Validation, and Simulation contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _stringify_uuid(v: Any) -> Any:
    if isinstance(v, UUID):
        return str(v)
    return v


class GraphNodeSchema(BaseModel):
    """Schema for a visual node in the workflow graph."""

    id: str
    type: str = Field(..., description="Node type: planner, research, coder, tester, reviewer, vision, condition, custom.")
    label: str
    config: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeSchema(BaseModel):
    """Schema for a visual edge connecting two nodes."""

    id: str
    source: str
    target: str
    condition: str | None = None


class WorkflowGraphJSONSchema(BaseModel):
    """Graph JSON topology representation."""

    nodes: list[GraphNodeSchema] = Field(default_factory=list)
    edges: list[GraphEdgeSchema] = Field(default_factory=list)


class WorkflowTemplateSchema(BaseModel):
    """Schema for a saved workflow template."""

    id: str
    name: str
    description: str
    graph_json: dict[str, Any]
    version: int
    is_preset: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v: Any) -> Any:
        return _stringify_uuid(v)


class CustomAgentSchema(BaseModel):
    """Schema for a user-defined custom agent."""

    id: str
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v: Any) -> Any:
        return _stringify_uuid(v)
    llm_model: str
    temperature: float
    retry_count: int
    allowed_mcp_tools: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateCustomAgentRequest(BaseModel):
    """Payload to create a new custom agent."""

    name: str = Field(..., description="Unique agent identifier name.")
    description: str = Field(default="", description="Description of the agent's role.")
    system_prompt: str = Field(..., description="System instructions for LLM.")
    user_prompt_template: str = Field(default="{input}", description="User prompt template.")
    llm_model: str = Field(default="llama3.1:8b", description="Target LLM model.")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    allowed_mcp_tools: list[str] = Field(default_factory=list)


class CreateWorkflowTemplateRequest(BaseModel):
    """Payload to create a new workflow template."""

    name: str = Field(..., description="Name of the workflow template.")
    description: str = Field(default="", description="Workflow description.")
    graph_json: dict[str, Any] = Field(..., description="Nodes and edges topology JSON.")


class ValidationReportSchema(BaseModel):
    """Report detailing graph topology validation results."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SimulationReportSchema(BaseModel):
    """Report detailing workflow execution simulation."""

    execution_order: list[str]
    estimated_runtime_seconds: float
    potential_failures: list[str] = Field(default_factory=list)
