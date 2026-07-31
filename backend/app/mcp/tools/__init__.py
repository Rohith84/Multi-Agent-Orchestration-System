"""
MCP Tools package.

Imports and registers all available MCP tools into the global registry.
"""

from app.mcp.tools.filesystem import register_filesystem_tools
from app.mcp.tools.postgres import register_postgres_tools
from app.mcp.tools.github import register_github_tools
from app.mcp.tools.http import register_http_tools
from app.mcp.tools.terminal import register_terminal_tools


def register_all_tools() -> None:
    """Register every MCP tool with the global ToolRegistry."""
    register_filesystem_tools()
    register_postgres_tools()
    register_github_tools()
    register_http_tools()
    register_terminal_tools()
