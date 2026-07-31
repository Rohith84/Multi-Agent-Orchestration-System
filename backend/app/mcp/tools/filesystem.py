"""
Filesystem MCP Tool Package.

Provides secure file system access restricted to the project workspace:
- Read/Write file contents
- Create/Update/Delete files
- Create directory, Move file, Copy file
- List directory contents & search files by pattern
"""

from __future__ import annotations

import os
import shutil
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
    """Read the contents of a file within the workspace."""
    resolved = _validate_path(path)

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not resolved.is_file():
        raise ValueError(f"Path is not a file: {path}")

    size = resolved.stat().st_size
    if size > 1_048_576:
        raise ValueError(f"File too large ({size} bytes). Maximum is 1MB.")

    content = resolved.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(resolved),
        "content": content,
        "size": size,
        "lines": content.count("\n") + 1,
    }


async def write_file(path: str, content: str) -> dict[str, Any]:
    """Write or overwrite a file inside the workspace."""
    resolved = _validate_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return {"path": str(resolved), "status": "written", "bytes": len(content)}


async def create_file(path: str, content: str = "") -> dict[str, Any]:
    """Create a new file inside the workspace."""
    resolved = _validate_path(path)
    if resolved.exists():
        raise FileExistsError(f"File already exists: {path}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return {"path": str(resolved), "status": "created", "bytes": len(content)}


async def update_file(path: str, content: str) -> dict[str, Any]:
    """Update content of an existing file."""
    resolved = _validate_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    resolved.write_text(content, encoding="utf-8")
    return {"path": str(resolved), "status": "updated", "bytes": len(content)}


async def delete_file(path: str) -> dict[str, Any]:
    """Delete a file from the workspace."""
    resolved = _validate_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()
    return {"path": str(resolved), "status": "deleted"}


async def create_directory(path: str) -> dict[str, Any]:
    """Create a directory in the workspace."""
    resolved = _validate_path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return {"path": str(resolved), "status": "directory_created"}


async def move_file(source: str, destination: str) -> dict[str, Any]:
    """Move or rename a file or directory."""
    src = _validate_path(source)
    dst = _validate_path(destination)
    if not src.exists():
        raise FileNotFoundError(f"Source path not found: {source}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return {"source": str(src), "destination": str(dst), "status": "moved"}


async def copy_file(source: str, destination: str) -> dict[str, Any]:
    """Copy a file within the workspace."""
    src = _validate_path(source)
    dst = _validate_path(destination)
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    else:
        shutil.copy2(str(src), str(dst))
    return {"source": str(src), "destination": str(dst), "status": "copied"}


async def list_directory(path: str = ".") -> dict[str, Any]:
    """List contents of a directory within the workspace."""
    resolved = _validate_path(path)

    if not resolved.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not resolved.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    entries = []
    for item in sorted(resolved.iterdir()):
        if item.name.startswith(".") or item.name in ("__pycache__", "node_modules", "venv", ".next", "chroma_db"):
            continue
        entry: dict[str, Any] = {
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
        }
        if item.is_file():
            entry["size"] = item.stat().st_size
        entries.append(entry)

    return {
        "path": str(resolved),
        "entries": entries,
        "count": len(entries),
    }


async def search_files(pattern: str, path: str = ".") -> dict[str, Any]:
    """Search for files matching a glob pattern within the workspace."""
    resolved = _validate_path(path)

    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"Search directory not found: {path}")

    matches = []
    workspace = _get_workspace_path()
    skip_dirs = {"__pycache__", "node_modules", "venv", ".next", ".git", "chroma_db"}

    for root, dirs, files in os.walk(resolved):
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

    tools = [
        ("filesystem.read_file", "Read file contents inside workspace", read_file, ["path"]),
        ("filesystem.write_file", "Write or overwrite file inside workspace", write_file, ["path", "content"]),
        ("filesystem.create_file", "Create new file inside workspace", create_file, ["path"]),
        ("filesystem.update_file", "Update existing file content", update_file, ["path", "content"]),
        ("filesystem.delete_file", "Delete file or folder", delete_file, ["path"]),
        ("filesystem.create_directory", "Create directory inside workspace", create_directory, ["path"]),
        ("filesystem.move_file", "Move or rename file inside workspace", move_file, ["source", "destination"]),
        ("filesystem.copy_file", "Copy file or folder inside workspace", copy_file, ["source", "destination"]),
        ("filesystem.list_directory", "List directory contents", list_directory, []),
        ("filesystem.search_files", "Search files matching glob pattern", search_files, ["pattern"]),
    ]

    for name, desc, handler, req_params in tools:
        registry.register(ToolDefinition(
            name=name,
            description=desc,
            category="filesystem",
            parameters={
                "properties": {p: {"type": "string", "description": f"{p} parameter"} for p in (req_params or ["path"])},
                "required": req_params,
            },
            handler=handler,
        ))

    logger.info("Extended MCP Filesystem tools registered")
