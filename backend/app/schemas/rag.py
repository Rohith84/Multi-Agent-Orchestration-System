"""
Pydantic schemas for RAG Execution States and Results.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RAGStatus(str, Enum):
    """Execution status for deterministic RAG retrieval classification."""

    RAG_SUCCESS = "RAG_SUCCESS"
    RAG_EMPTY = "RAG_EMPTY"
    RAG_INFRASTRUCTURE_ERROR = "RAG_INFRASTRUCTURE_ERROR"


class RAGResult(BaseModel):
    """Structured result returned by retriever / Knowledge Base queries."""

    status: RAGStatus = Field(..., description="RAG status classification")
    chunks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved document chunks",
    )
    error: str | None = Field(
        default=None,
        description="Error details if an infrastructure failure occurred",
    )
    retrieval_time: float = Field(
        default=0.0,
        description="Time taken to perform retrieval in seconds",
    )

    model_config = ConfigDict(use_enum_values=True)
