"""Global exception handler registration for the FlashiFi API.

Provides a single ``register_error_handlers`` function that attaches
exception handlers to a FastAPI application instance. All handlers
serialise errors through :class:`~app.schemas.errors.ErrorResponse` to
guarantee a uniform JSON contract.

Handled exception categories:

1. **FlashiFiError** (and subclasses) — domain-specific errors raised
   intentionally by business logic (e.g. ``InvalidInputError``,
   ``TaskNotFoundError``). Logged at WARNING level.
2. **RequestValidationError** — Pydantic / FastAPI request-body and
   query-parameter validation failures. Logged at WARNING level.
   Returns HTTP 422.
3. **Exception** (catch-all) — any unhandled exception. Logged at ERROR
   level with full traceback. Returns a generic HTTP 500 message that
   does **not** leak internal details.

Every handler reads ``request.state.request_id`` (set by
:class:`~app.middleware.request_id.RequestIDMiddleware`) and includes it
in the response body for end-to-end tracing.

Functions:
    register_error_handlers: Attach all handlers to a FastAPI app.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.handlers import FlashiFiError
from app.schemas.errors import ErrorResponse


logger: logging.Logger = logging.getLogger("flashifi.errors")
"""Module-level logger for error events."""


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on a FastAPI application.

    This function should be called once during application startup
    (typically in the app factory) **after** middleware has been added,
    so that ``request.state.request_id`` is available.

    Args:
        app: The FastAPI application instance to attach handlers to.

    Example::

        from fastapi import FastAPI
        from app.middleware.error_handler import register_error_handlers

        app = FastAPI()
        register_error_handlers(app)
    """

    # ------------------------------------------------------------------
    # 1. Domain-specific errors (FlashiFiError hierarchy)
    # ------------------------------------------------------------------
    @app.exception_handler(FlashiFiError)
    async def flashifi_error_handler(
        request: Request,
        exc: FlashiFiError,
    ) -> JSONResponse:
        """Handle intentional domain errors raised by business logic.

        Args:
            request: The incoming HTTP request.
            exc: The domain-specific error instance.

        Returns:
            A JSON response with the appropriate HTTP status code and
            an :class:`ErrorResponse` body.
        """
        request_id: str | None = getattr(
            request.state, "request_id", None
        )

        logger.warning(
            "FlashiFi error: %s",
            exc.detail,
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "error_type": type(exc).__name__,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=type(exc).__name__,
                detail=exc.detail,
                request_id=request_id,
            ).model_dump(),
        )

    # ------------------------------------------------------------------
    # 2. Pydantic / FastAPI validation errors
    # ------------------------------------------------------------------
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle request validation errors (malformed payloads, bad types).

        Args:
            request: The incoming HTTP request.
            exc: The validation error raised by Pydantic / FastAPI.

        Returns:
            A 422 JSON response with validation error details.
        """
        request_id: str | None = getattr(
            request.state, "request_id", None
        )

        logger.warning(
            "Validation error: %s",
            str(exc),
            extra={"request_id": request_id},
        )

        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="ValidationError",
                detail=str(exc),
                request_id=request_id,
            ).model_dump(),
        )

    # ------------------------------------------------------------------
    # 3. Catch-all for unhandled exceptions
    # ------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def generic_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle any unhandled exception with a safe 500 response.

        The full traceback is logged at ERROR level, but the response
        body intentionally omits internal details to prevent information
        leakage.

        Args:
            request: The incoming HTTP request.
            exc: The unhandled exception.

        Returns:
            A generic 500 JSON response.
        """
        request_id: str | None = getattr(
            request.state, "request_id", None
        )

        logger.exception(
            "Unhandled exception",
            extra={"request_id": request_id},
        )

        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="InternalServerError",
                detail=(
                    "An unexpected error occurred. Please try again later."
                ),
                request_id=request_id,
            ).model_dump(),
        )
