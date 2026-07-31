"""
Filesystem MCP Tool.

Provides secure file system access restricted to the project workspace:
- Read file contents
- List directory contents
- Search files by pattern
"""

from __future__ import annotations

import os
import fnmatch
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.mcp.registry import ToolRegistry, ToolDefinition

logger = get_logger(__name__)


def _get_workspace_path() -> Path:
    """Return the resolved workspace root path."""
    settings = get_settings()
    return Path(settings.mcp_workspace_path).resolve()


def _validate_path(requested_path: str) -> Path:
    """
    Validate that the requested path is within the workspace.

    Raises PermissionError if path traversal is detected.
    """
    workspace = _get_workspace_path()
    resolved = (workspace / requested_path).resolve()

    if not str(resolved).startswith(str(workspace)):
        raise PermissionError(
            f"Access denied: path '{requested_path}' is outside the workspace."
        )

    return resolved


async def read_file(path: str) -> dict[str, Any]:
    """
    Read the contents of a file within the workspace.

    Args:
        path: Relative path from workspace root.

    Returns:
        Dict with file path, content, and size.
    """
    resolved = _validate_path(path)

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not resolved.is_file():
        raise ValueError(f"Path is not a file: {path}")

    # Limit file size to 1MB
    size = resolved.stat().st_size
    if size > 1_048_576:
        raise ValueError(f"File too large ({size} bytes). Maximum is 1MB.")

    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Cannot read file: {e}")

    return {
        "path": str(resolved),
        "content": content,
        "size": size,
        "lines": content.count("\n") + 1,
    }


async def list_directory(path: str = ".") -> dict[str, Any]:
    """
    List contents of a directory within the workspace.

    Args:
        path: Relative path from workspace root. Defaults to root.

    Returns:
        Dict with directory path and list of entries.
    """
    resolved = _validate_path(path)

    if not resolved.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if not resolved.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    entries = []
    try:
        for item in sorted(resolved.iterdir()):
            # Skip hidden files, __pycache__, node_modules, .git, venv
            if item.name.startswith(".") or item.name in (
                "__pycache__",
                "node_modules",
                "venv",
                ".next",
                "chroma_db",
            ):
                continue

            entry: dict[str, Any] = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
            }
            if item.is_file():
                entry["size"] = item.stat().st_size
            entries.append(entry)
    except PermissionError:
        raise PermissionError(f"Permission denied reading directory: {path}")

    return {
        "path": str(resolved),
        "entries": entries,
        "count": len(entries),
    }


async def search_files(pattern: str, path: str = ".") -> dict[str, Any]:
    """
    Search for files matching a glob pattern within the workspace.

    Args:
        pattern: Glob pattern (e.g. '*.py', '*.ts').
        path: Relative path to search from. Defaults to root.

    Returns:
        Dict with matching file paths.
    """
    resolved = _validate_path(path)

    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"Search directory not found: {path}")

    matches = []
    workspace = _get_workspace_path()
    skip_dirs = {"__pycache__", "node_modules", "venv", ".next", ".git", "chroma_db"}

    for root, dirs, files in os.walk(resolved):
        # Prune skipped directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]

        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(workspace)
                matches.append({
                    "path": str(rel_path),
                    "name": filename,
                    "size": full_path.stat().st_size,
                })

        # Limit results
        if len(matches) >= 100:
            break

    return {
        "pattern": pattern,
        "search_path": str(resolved),
        "matches": matches,
        "count": len(matches),
        "truncated": len(matches) >= 100,
    }


def register_filesystem_tools() -> None:
    """Register all filesystem tools with the MCP registry."""
    registry = ToolRegistry.instance()

    registry.register(ToolDefinition(
        name="filesystem.read_file",
        description="Read the contents of a file within the project workspace.",
        category="filesystem",
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from workspace root.",
                },
            },
            "required": ["path"],
        },
        handler=read_file,
    ))

    registry.register(ToolDefinition(
        name="filesystem.list_directory",
        description="List contents of a directory within the project workspace.",
        category="filesystem",
        parameters={
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from workspace root. Defaults to '.'.",
                },
            },
            "required": [],
        },
        handler=list_directory,
    ))

    registry.register(ToolDefinition(
        name="filesystem.search_files",
        description="Search for files matching a glob pattern within the workspace.",
        category="filesystem",
        parameters={
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g. '*.py', '*.ts').",
                },
                "path": {
                    "type": "string",
                    "description": "Relative path to search from. Defaults to '.'.",
                },
            },
            "required": ["pattern"],
        },
        handler=search_files,
    ))

    logger.info("Filesystem tools registered")
