"""
Pydantic schemas for Agent Reasoning Metadata.
Explanatory metadata for LLM reasoning decisions. Non-authoritative.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReasoningMetadata(BaseModel):
    """
    Non-authoritative external reasoning metadata summary produced by agents.
    Does NOT act as an execution gate or override deterministic validation states.
    """

    decision: str = Field(default="", description="Core decision or technical approach chosen")
    evidence_used: list[str] = Field(default_factory=list, description="References to evidence or context used")
    rationale: str = Field(default="", description="Explanation for why this decision/approach was chosen")
    alternatives_considered: list[str] = Field(default_factory=list, description="Alternative approaches evaluated")
    trade_offs: list[str] = Field(default_factory=list, description="Trade-offs identified in the chosen approach")
    risks: list[str] = Field(default_factory=list, description="Identified technical risks or uncertainties")
    implementation_implications: list[str] = Field(
        default_factory=list,
        description="Downstream architectural or implementation implications",
    )

    model_config = ConfigDict(extra="ignore")
