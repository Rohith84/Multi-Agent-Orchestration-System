"""
MCP Tool Registry.

Centralized registry for all MCP tools. Provides:
- Tool registration with schema definitions
- Tool lookup and listing
- Tool execution dispatch with validation
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """Schema describing a registered MCP tool."""

    name: str
    description: str
    category: str
    parameters: dict[str, Any]
    handler: Callable[..., Awaitable[dict[str, Any]]]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict (excludes handler)."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """
    Singleton registry holding all available MCP tools.

    Usage:
        registry = ToolRegistry.instance()
        registry.register(ToolDefinition(...))
        tool = registry.get_tool("filesystem.read_file")
    """

    _instance: ToolRegistry | None = None

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    @classmethod
    def instance(cls) -> ToolRegistry:
        """Return the global singleton registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — used for testing."""
        cls._instance = None

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition. Overwrites if name already exists."""
        self._tools[tool.name] = tool
        logger.info("Registered MCP tool: %s (%s)", tool.name, tool.category)

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get a tool by name, or None."""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())

    def list_tool_names(self) -> list[str]:
        """Return sorted list of tool names."""
        return sorted(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a tool by name with provided arguments.

        Returns a dict with keys: success, result/error.
        Raises ValueError if tool is not found.
        """
        tool = self.get_tool(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' is not registered.")

        # Validate required parameters
        required = tool.parameters.get("required", [])
        properties = tool.parameters.get("properties", {})
        for param_name in required:
            if param_name not in arguments:
                raise ValueError(
                    f"Missing required parameter '{param_name}' for tool '{name}'."
                )

        # Validate parameter types (basic)
        for param_name, value in arguments.items():
            if param_name not in properties:
                raise ValueError(
                    f"Unknown parameter '{param_name}' for tool '{name}'. "
                    f"Valid parameters: {list(properties.keys())}"
                )

        logger.info("Executing MCP tool: %s with args: %s", name, list(arguments.keys()))

        try:
            result = await tool.handler(**arguments)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error("Tool '%s' execution failed: %s", name, str(e))
            return {"success": False, "error": str(e)}
