"""
GitHub MCP Tool.

Provides read-only access to GitHub repositories:
- Repository info
- Branches
- Commits
- Pull Requests
- Issues

Uses the GITHUB_TOKEN environment variable for authentication.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.mcp.registry import ToolRegistry, ToolDefinition

logger = get_logger(__name__)

_GITHUB_API = "https://api.github.com"
_TIMEOUT = 15.0


def _get_headers() -> dict[str, str]:
    """Build request headers with optional auth token."""
    settings = get_settings()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MultiAgent-MCP/1.0",
    }
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    return headers


async def _github_get(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Make an authenticated GET request to the GitHub API."""
    url = f"{_GITHUB_API}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, headers=_get_headers(), params=params)

            if response.status_code == 404:
                raise ValueError(f"GitHub resource not found: {endpoint}")
            if response.status_code == 403:
                raise PermissionError("GitHub API rate limit exceeded or token invalid.")
            if response.status_code == 401:
                raise PermissionError("GitHub authentication failed. Check GITHUB_TOKEN.")

            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise ConnectionError("Cannot connect to GitHub API.")
    except httpx.TimeoutException:
        raise TimeoutError("GitHub API request timed out.")


async def read_repository(owner: str, repo: str) -> dict[str, Any]:
    """
    Get repository information.

    Args:
        owner: Repository owner/organization.
        repo: Repository name.
    """
    data = await _github_get(f"/repos/{owner}/{repo}")
    return {
        "name": data.get("full_name"),
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "default_branch": data.get("default_branch"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "url": data.get("html_url"),
    }


async def list_branches(owner: str, repo: str) -> dict[str, Any]:
    """
    List branches of a repository.

    Args:
        owner: Repository owner/organization.
        repo: Repository name.
    """
    data = await _github_get(f"/repos/{owner}/{repo}/branches", params={"per_page": 30})
    branches = [
        {"name": b["name"], "protected": b.get("protected", False)}
        for b in data
    ]
    return {"branches": branches, "count": len(branches)}


async def list_commits(owner: str, repo: str, branch: str = "main") -> dict[str, Any]:
    """
    List recent commits of a repository.

    Args:
        owner: Repository owner/organization.
        repo: Repository name.
        branch: Branch name. Defaults to 'main'.
    """
    data = await _github_get(
        f"/repos/{owner}/{repo}/commits",
        params={"sha": branch, "per_page": 20},
    )
    commits = [
        {
            "sha": c["sha"][:7],
            "message": c["commit"]["message"].split("\n")[0],
            "author": c["commit"]["author"]["name"],
            "date": c["commit"]["author"]["date"],
        }
        for c in data
    ]
    return {"branch": branch, "commits": commits, "count": len(commits)}


async def list_pull_requests(owner: str, repo: str) -> dict[str, Any]:
    """
    List open pull requests of a repository.

    Args:
        owner: Repository owner/organization.
        repo: Repository name.
    """
    data = await _github_get(
        f"/repos/{owner}/{repo}/pulls",
        params={"state": "open", "per_page": 20},
    )
    prs = [
        {
            "number": pr["number"],
            "title": pr["title"],
            "author": pr["user"]["login"],
            "state": pr["state"],
            "created_at": pr["created_at"],
            "url": pr["html_url"],
        }
        for pr in data
    ]
    return {"pull_requests": prs, "count": len(prs)}


async def list_issues(owner: str, repo: str) -> dict[str, Any]:
    """
    List open issues of a repository.

    Args:
        owner: Repository owner/organization.
        repo: Repository name.
    """
    data = await _github_get(
        f"/repos/{owner}/{repo}/issues",
        params={"state": "open", "per_page": 20},
    )
    # Filter out pull requests (GitHub API returns PRs as issues too)
    issues = [
        {
            "number": issue["number"],
            "title": issue["title"],
            "author": issue["user"]["login"],
            "state": issue["state"],
            "labels": [l["name"] for l in issue.get("labels", [])],
            "created_at": issue["created_at"],
            "url": issue["html_url"],
        }
        for issue in data
        if "pull_request" not in issue
    ]
    return {"issues": issues, "count": len(issues)}


def register_github_tools() -> None:
    """Register all GitHub tools with the MCP registry."""
    registry = ToolRegistry.instance()

    registry.register(ToolDefinition(
        name="github.read_repository",
        description="Get information about a GitHub repository.",
        category="github",
        parameters={
            "properties": {
                "owner": {"type": "string", "description": "Repository owner or organization."},
                "repo": {"type": "string", "description": "Repository name."},
            },
            "required": ["owner", "repo"],
        },
        handler=read_repository,
    ))

    registry.register(ToolDefinition(
        name="github.list_branches",
        description="List branches of a GitHub repository.",
        category="github",
        parameters={
            "properties": {
                "owner": {"type": "string", "description": "Repository owner."},
                "repo": {"type": "string", "description": "Repository name."},
            },
            "required": ["owner", "repo"],
        },
        handler=list_branches,
    ))

    registry.register(ToolDefinition(
        name="github.list_commits",
        description="List recent commits of a GitHub repository branch.",
        category="github",
        parameters={
            "properties": {
                "owner": {"type": "string", "description": "Repository owner."},
                "repo": {"type": "string", "description": "Repository name."},
                "branch": {"type": "string", "description": "Branch name. Defaults to 'main'."},
            },
            "required": ["owner", "repo"],
        },
        handler=list_commits,
    ))

    registry.register(ToolDefinition(
        name="github.list_pull_requests",
        description="List open pull requests of a GitHub repository.",
        category="github",
        parameters={
            "properties": {
                "owner": {"type": "string", "description": "Repository owner."},
                "repo": {"type": "string", "description": "Repository name."},
            },
            "required": ["owner", "repo"],
        },
        handler=list_pull_requests,
    ))

    registry.register(ToolDefinition(
        name="github.list_issues",
        description="List open issues of a GitHub repository.",
        category="github",
        parameters={
            "properties": {
                "owner": {"type": "string", "description": "Repository owner."},
                "repo": {"type": "string", "description": "Repository name."},
            },
            "required": ["owner", "repo"],
        },
        handler=list_issues,
    ))

    logger.info("GitHub tools registered")
