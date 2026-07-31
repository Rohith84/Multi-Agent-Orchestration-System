"""
HTTP MCP Tool.

Generic HTTP client for calling external REST APIs:
- GET, POST, PUT, DELETE
- Configurable timeout
- Response size limiting
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.mcp.registry import ToolRegistry, ToolDefinition

logger = get_logger(__name__)

_MAX_TIMEOUT = 60.0
_DEFAULT_TIMEOUT = 30.0
_MAX_RESPONSE_SIZE = 512_000  # 512KB


async def http_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """
    Make an HTTP request to an external URL.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE).
        url: Target URL.
        headers: Optional request headers.
        body: Optional request body (JSON).
        timeout: Request timeout in seconds. Default 30, max 60.

    Returns:
        Dict with status code, headers, and response body.
    """
    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE"):
        raise ValueError(f"Unsupported HTTP method: {method}. Use GET, POST, PUT, or DELETE.")

    # Validate URL
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    # Clamp timeout
    req_timeout = min(timeout or _DEFAULT_TIMEOUT, _MAX_TIMEOUT)

    request_headers = {"User-Agent": "MultiAgent-MCP/1.0"}
    if headers:
        request_headers.update(headers)

    try:
        async with httpx.AsyncClient(timeout=req_timeout) as client:
            if method == "GET":
                response = await client.get(url, headers=request_headers)
            elif method == "POST":
                response = await client.post(url, headers=request_headers, json=body)
            elif method == "PUT":
                response = await client.put(url, headers=request_headers, json=body)
            elif method == "DELETE":
                response = await client.delete(url, headers=request_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Limit response size
            content = response.text
            truncated = False
            if len(content) > _MAX_RESPONSE_SIZE:
                content = content[:_MAX_RESPONSE_SIZE]
                truncated = True

            # Parse response headers
            resp_headers = dict(response.headers)
            # Remove potentially sensitive headers
            for key in ("set-cookie", "authorization"):
                resp_headers.pop(key, None)

            return {
                "status_code": response.status_code,
                "headers": resp_headers,
                "body": content,
                "content_length": len(content),
                "truncated": truncated,
            }

    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to {url}")
    except httpx.TimeoutException:
        raise TimeoutError(f"Request to {url} timed out after {req_timeout}s")
    except httpx.HTTPError as e:
        raise ValueError(f"HTTP error: {str(e)}")


def register_http_tools() -> None:
    """Register HTTP tools with the MCP registry."""
    registry = ToolRegistry.instance()

    registry.register(ToolDefinition(
        name="http.request",
        description="Make an HTTP request to an external URL. Supports GET, POST, PUT, DELETE.",
        category="http",
        parameters={
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method: GET, POST, PUT, or DELETE.",
                },
                "url": {
                    "type": "string",
                    "description": "Target URL (must start with http:// or https://).",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional request headers as key-value pairs.",
                },
                "body": {
                    "type": "object",
                    "description": "Optional request body (JSON). Used with POST/PUT.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds. Default 30, max 60.",
                },
            },
            "required": ["method", "url"],
        },
        handler=http_request,
    ))

    logger.info("HTTP tools registered")
