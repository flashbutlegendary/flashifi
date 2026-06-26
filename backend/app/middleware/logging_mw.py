"""Structured access-logging middleware for the FlashiFi API.

Logs every HTTP request/response cycle with:
- HTTP method, path, and status code
- Duration in milliseconds (via ``time.perf_counter``)
- Client IP address
- Request ID (from :class:`~app.middleware.request_id.RequestIDMiddleware`)

Log levels are chosen dynamically based on the response status code:
- **INFO** for 2xx/3xx responses
- **WARNING** for 4xx responses
- **ERROR** for 5xx responses

Certain paths (e.g. ``/health``) can be excluded to reduce noise from
high-frequency probes.

Classes:
    LoggingMiddleware: Starlette ``BaseHTTPMiddleware`` that produces
        structured access logs.
"""

from __future__ import annotations

import logging
import time
from typing import ClassVar

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response


logger: logging.Logger = logging.getLogger("flashifi.access")
"""Module-level logger for access log entries."""


class LoggingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that emits a structured log line per request.

    Attributes:
        SKIP_PATHS: A set of URL paths that should **not** be logged.
            Defaults to ``{"/health"}`` to suppress noisy liveness probes.

    Example::

        from fastapi import FastAPI
        from app.middleware.logging_mw import LoggingMiddleware

        app = FastAPI()
        app.add_middleware(LoggingMiddleware)
    """

    SKIP_PATHS: ClassVar[set[str]] = {"/health"}
    """Paths excluded from access logging (e.g. health-check endpoints)."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Intercept the request, time the downstream processing, and log.

        Args:
            request: The incoming HTTP request.
            call_next: Callable that forwards the request to the next
                middleware or the route handler.

        Returns:
            The unmodified HTTP response from the downstream handler.
        """
        # Skip logging for noise-heavy paths.
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start: float = time.perf_counter()

        response: Response = await call_next(request)

        duration_ms: float = (time.perf_counter() - start) * 1000

        # Retrieve the request ID set by RequestIDMiddleware.
        request_id: str = getattr(request.state, "request_id", "unknown")

        # Safely resolve the client IP.
        client_ip: str = (
            request.client.host if request.client else "unknown"
        )

        log_data: dict[str, object] = {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
        }

        # Choose log level based on HTTP status code.
        level: int = _status_to_log_level(response.status_code)

        logger.log(level, "request_completed", extra=log_data)

        return response


def _status_to_log_level(status_code: int) -> int:
    """Map an HTTP status code to the appropriate Python log level.

    Args:
        status_code: The HTTP response status code.

    Returns:
        ``logging.INFO`` for 1xx–3xx, ``logging.WARNING`` for 4xx,
        ``logging.ERROR`` for 5xx and above.
    """
    if status_code < 400:
        return logging.INFO
    if status_code < 500:
        return logging.WARNING
    return logging.ERROR
