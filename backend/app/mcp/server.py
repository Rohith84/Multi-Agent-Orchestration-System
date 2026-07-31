"""
MCP Server.

In-process MCP server that handles JSON-RPC-style tool invocations.
Wraps the ToolRegistry and provides:
- Request validation
- Audit logging
- Structured responses
"""

from __future__ import annotations

import time
from typing import Any
from dataclasses import dataclass

from app.core.logging import get_logger
from app.mcp.registry import ToolRegistry

logger = get_logger(__name__)


@dataclass
class MCPRequest:
    """JSON-RPC-style request for tool invocation."""
    method: str
    params: dict[str, Any]
    id: str | None = None


@dataclass
class MCPResponse:
    """JSON-RPC-style response from tool invocation."""
    success: bool
    result: Any = None
    error: str | None = None
    execution_time: float = 0.0
    tool_name: str = ""
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        data: dict[str, Any] = {
            "success": self.success,
            "tool_name": self.tool_name,
            "execution_time": round(self.execution_time, 4),
        }
        if self.id is not None:
            data["id"] = self.id
        if self.success:
            data["result"] = self.result
        else:
            data["error"] = self.error
        return data


class MCPServer:
    """
    In-process MCP server.

    Handles JSON-RPC-style requests, executes tools via the registry,
    and returns structured responses with timing and audit logs.
    """

    def __init__(self) -> None:
        self.registry = ToolRegistry.instance()
        self._initialized = False

    def initialize(self) -> None:
        """Mark server as initialized after tool registration."""
        self._initialized = True
        tool_count = len(self.registry.list_tools())
        logger.info("MCP Server initialized with %d tools", tool_count)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Process an MCP request and return a structured response.

        Validates the request, executes the tool, logs the invocation,
        and returns timing information.
        """
        tool_name = request.method
        start_time = time.time()

        logger.info(
            "MCP Request: tool=%s, params=%s",
            tool_name,
            list(request.params.keys()),
        )

        # Validate tool exists
        if not self.registry.has_tool(tool_name):
            elapsed = time.time() - start_time
            logger.warning("MCP tool not found: %s", tool_name)
            return MCPResponse(
                success=False,
                error=f"Tool '{tool_name}' not found. Available: {self.registry.list_tool_names()}",
                execution_time=elapsed,
                tool_name=tool_name,
                id=request.id,
            )

        try:
            result = await self.registry.execute(tool_name, request.params)
            elapsed = time.time() - start_time

            if result["success"]:
                logger.info(
                    "MCP tool '%s' executed successfully in %.4fs",
                    tool_name,
                    elapsed,
                )
                return MCPResponse(
                    success=True,
                    result=result["result"],
                    execution_time=elapsed,
                    tool_name=tool_name,
                    id=request.id,
                )
            else:
                logger.error(
                    "MCP tool '%s' returned error in %.4fs: %s",
                    tool_name,
                    elapsed,
                    result["error"],
                )
                return MCPResponse(
                    success=False,
                    error=result["error"],
                    execution_time=elapsed,
                    tool_name=tool_name,
                    id=request.id,
                )

        except ValueError as e:
            elapsed = time.time() - start_time
            logger.error("MCP validation error for '%s': %s", tool_name, str(e))
            return MCPResponse(
                success=False,
                error=str(e),
                execution_time=elapsed,
                tool_name=tool_name,
                id=request.id,
            )
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("MCP unexpected error for '%s': %s", tool_name, str(e))
            return MCPResponse(
                success=False,
                error=f"Internal error: {str(e)}",
                execution_time=elapsed,
                tool_name=tool_name,
                id=request.id,
            )

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all tools as JSON-serializable dicts."""
        return [tool.to_dict() for tool in self.registry.list_tools()]


# Global MCP server singleton
_mcp_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    """Get or create the global MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server
