"""
Deterministic Graph Contract Validator.

Enforces structural and topological invariants on dynamic LangGraph definitions
before any StateGraph nodes or edges are compiled.
"""

from __future__ import annotations

from typing import Any
from pydantic import ValidationError

from app.core.logging import get_logger
from app.schemas.contracts import GraphContract

logger = get_logger(__name__)


class GraphContractValidationError(Exception):
    """Exception raised when a dynamic graph definition violates the GraphContract."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or [message]


class GraphValidationResult:
    """Result of graph contract validation."""

    def __init__(
        self,
        is_valid: bool,
        contract: GraphContract | None = None,
        errors: list[str] | None = None,
    ) -> None:
        self.is_valid = is_valid
        self.contract = contract
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "contract": self.contract.model_dump() if self.contract else None,
            "errors": self.errors,
        }


class GraphContractValidator:
    """
    Deterministic validator for dynamic workflow graphs.

    Guarantees:
    - Node IDs exist, are non-empty, and unique.
    - Supported node types (planner, research, coder, tester, reviewer, custom).
    - Edge sources and targets exist and reference real nodes.
    - Duplicate edges and self-loops are rejected.
    - Directed cycles (A -> B -> A) are detected and rejected.
    - Unreachable nodes are detected and rejected.
    - Empty graphs and excessive size graphs (>20 nodes) are rejected.
    - Invalid graphs are never compiled into StateGraphs.
    """

    @classmethod
    def validate(cls, graph_input: GraphContract | dict[str, Any]) -> GraphValidationResult:
        """
        Validate a GraphContract instance or a graph dictionary (with 'nodes' and 'edges').
        """
        if isinstance(graph_input, GraphContract):
            return GraphValidationResult(is_valid=True, contract=graph_input)

        if isinstance(graph_input, dict):
            try:
                contract = GraphContract(**graph_input)
                return GraphValidationResult(is_valid=True, contract=contract)
            except ValidationError as ve:
                err_msgs = [e["msg"] for e in ve.errors()]
                logger.warning("GraphContract validation failed: %s", err_msgs)
                return GraphValidationResult(is_valid=False, errors=err_msgs)
            except Exception as e:
                logger.warning("GraphContract validation failed: %s", e)
                return GraphValidationResult(is_valid=False, errors=[str(e)])

        return GraphValidationResult(
            is_valid=False,
            errors=[f"Unsupported graph input type: {type(graph_input).__name__}"],
        )

    @classmethod
    def validate_or_raise(cls, graph_input: GraphContract | dict[str, Any]) -> GraphContract:
        """
        Validate graph and return the validated GraphContract, or raise GraphContractValidationError.
        """
        res = cls.validate(graph_input)
        if not res.is_valid or res.contract is None:
            err_summary = "; ".join(res.errors)
            logger.error("Rejecting invalid graph definition: %s", err_summary)
            raise GraphContractValidationError(
                f"Graph Contract Violation: {err_summary}", errors=res.errors
            )
        return res.contract
