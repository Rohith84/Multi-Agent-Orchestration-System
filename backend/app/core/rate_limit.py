"""
Rate Limiting Middleware.

Limits API request rates per client IP address.
"""

from __future__ import annotations

import time
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)

# Default rate limit: 120 requests per minute per IP
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60

_client_request_history: dict[str, list[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware enforcing configurable request rate limits.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exclude static assets or health probes from rate limits
        path = request.url.path
        if path.startswith(("/docs", "/openapi.json", "/api/health", "/api/liveness", "/api/readiness")):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()

        # Clean old timestamps outside the window
        timestamps = [t for t in _client_request_history.get(client_ip, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]

        if len(timestamps) >= RATE_LIMIT_REQUESTS:
            logger.warning("Rate limit exceeded for client IP: %s (path=%s)", client_ip, path)
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down requests.")

        timestamps.append(now)
        _client_request_history[client_ip] = timestamps

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT_REQUESTS - len(timestamps))
        return response
