"""
MCP Tool Runner.

Bridge between LangGraph agents and the MCP server.
Provides a simple interface for agents to invoke MCP tools,
with timing, error handling, and structured result collection.
"""

from __future__ import annotations

import time
import json
from typing import Any
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.mcp.server import MCPServer, MCPRequest, get_mcp_server

logger = get_logger(__name__)


@dataclass
class ToolInvocationRecord:
    """Record of a single tool invocation during agent execution."""
    agent_name: str
    tool_name: str
    arguments: dict[str, Any]
    status: str  # "success" | "failed"
    execution_time: float
    result_summary: str


class MCPToolRunner:
    """
    Agent-facing MCP tool client.

    Used by agents to invoke MCP tools before/after their LLM calls.
    Collects invocation records for SSE streaming and DB persistence.
    """

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.server: MCPServer = get_mcp_server()
        self.invocations: list[ToolInvocationRecord] = []

    async def run_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Invoke an MCP tool and return its result.

        Args:
            tool_name: Name of the tool (e.g. 'filesystem.read_file').
            arguments: Tool arguments dict.

        Returns:
            The tool result dict if successful, None if failed.
            Failures are logged but do not raise — agents degrade gracefully.
        """
        arguments = arguments or {}
        start_time = time.time()

        logger.info(
            "[%s] Invoking MCP tool: %s (args=%s)",
            self.agent_name,
            tool_name,
            list(arguments.keys()),
        )

        try:
            request = MCPRequest(
                method=tool_name,
                params=arguments,
                id=f"{self.agent_name}-{tool_name}-{int(time.time())}",
            )

            response = await self.server.handle_request(request)
            elapsed = time.time() - start_time

            # Build result summary
            if response.success:
                summary = self._summarize_result(response.result)
                status = "success"
            else:
                summary = response.error or "Unknown error"
                status = "failed"

            # Record the invocation
            self.invocations.append(ToolInvocationRecord(
                agent_name=self.agent_name,
                tool_name=tool_name,
                arguments=arguments,
                status=status,
                execution_time=round(elapsed, 4),
                result_summary=summary[:500],
            ))

            if response.success:
                logger.info(
                    "[%s] Tool '%s' succeeded in %.4fs",
                    self.agent_name,
                    tool_name,
                    elapsed,
                )
                return response.result
            else:
                logger.warning(
                    "[%s] Tool '%s' failed in %.4fs: %s",
                    self.agent_name,
                    tool_name,
                    elapsed,
                    response.error,
                )
                return None

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "[%s] Tool '%s' raised exception in %.4fs: %s",
                self.agent_name,
                tool_name,
                elapsed,
                str(e),
            )
            self.invocations.append(ToolInvocationRecord(
                agent_name=self.agent_name,
                tool_name=tool_name,
                arguments=arguments,
                status="failed",
                execution_time=round(elapsed, 4),
                result_summary=str(e)[:500],
            ))
            return None

    def get_invocations(self) -> list[ToolInvocationRecord]:
        """Return all tool invocation records for this agent run."""
        return self.invocations

    def clear_invocations(self) -> None:
        """Clear invocation records."""
        self.invocations.clear()

    def _summarize_result(self, result: Any, max_len: int = 500) -> str:
        """Create a brief summary of a tool result for storage."""
        if result is None:
            return "No result"
        if isinstance(result, str):
            return result[:max_len]
        if isinstance(result, dict):
            # Remove large fields for summary
            summary = {}
            for key, value in result.items():
                if isinstance(value, str) and len(value) > 200:
                    summary[key] = f"[{len(value)} chars]"
                elif isinstance(value, list) and len(value) > 10:
                    summary[key] = f"[{len(value)} items]"
                else:
                    summary[key] = value
            return json.dumps(summary, default=str)[:max_len]
        return str(result)[:max_len]
