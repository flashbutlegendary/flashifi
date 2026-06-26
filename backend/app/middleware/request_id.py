"""Request ID middleware for the FlashiFi API.

Ensures every incoming HTTP request is tagged with a unique identifier
that flows through the entire request lifecycle — from logging to error
responses. If the client supplies an ``X-Request-ID`` header, that value
is reused; otherwise a new UUID4 is generated.

The request ID is:
1. Stored in ``request.state.request_id`` for downstream handlers.
2. Echoed back in the ``X-Request-ID`` response header.

This enables end-to-end request tracing across client, API gateway, and
backend logs.

Classes:
    RequestIDMiddleware: Starlette ``BaseHTTPMiddleware`` that manages
        request IDs.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response


_REQUEST_ID_HEADER: str = "x-request-id"
"""Lowercase header name used for lookups (HTTP headers are case-insensitive)."""

_RESPONSE_ID_HEADER: str = "X-Request-ID"
"""Canonical casing used in the outgoing response header."""


class RequestIDMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that assigns a unique request ID to every request.

    Behaviour:
        * If the incoming request contains an ``X-Request-ID`` header, its
          value is reused verbatim.
        * Otherwise, a new UUID4 string is generated.
        * The resolved ID is stored on ``request.state.request_id`` so that
          downstream middleware, route handlers, and exception handlers can
          access it without parsing headers.
        * The ID is always set on the ``X-Request-ID`` response header,
          regardless of origin.

    Example::

        from fastapi import FastAPI
        from app.middleware.request_id import RequestIDMiddleware

        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/")
        async def root(request: Request) -> dict[str, str]:
            return {"request_id": request.state.request_id}
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request, attaching a request ID.

        Args:
            request: The incoming HTTP request.
            call_next: Callable that forwards the request to the next
                middleware or the route handler.

        Returns:
            The HTTP response with the ``X-Request-ID`` header set.
        """
        # Prefer a client-supplied request ID; fall back to a new UUID4.
        request_id: str = request.headers.get(
            _REQUEST_ID_HEADER,
            str(uuid.uuid4()),
        )

        # Store on request state for downstream consumers.
        request.state.request_id = request_id

        # Forward to the next handler.
        response: Response = await call_next(request)

        # Echo the request ID back to the client.
        response.headers[_RESPONSE_ID_HEADER] = request_id

        return response
