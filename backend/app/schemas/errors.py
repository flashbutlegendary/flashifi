"""Error response schema for the FlashiFi API.

This module defines the standard error envelope returned by all exception
handlers. Every error response — whether from validation failures, custom
business-logic errors, or unhandled exceptions — is serialized through
this model to guarantee a consistent contract for API consumers.

Classes:
    ErrorResponse: Standard error envelope returned by all error handlers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response returned by all error handlers.

    Provides a machine-readable error type, a human-readable description,
    and an optional request tracking ID for correlation in logs.

    Attributes:
        error: A short, PascalCase error type identifier
            (e.g. ``"ValidationError"``, ``"TaskNotFoundError"``).
        detail: A human-readable description of what went wrong.
        request_id: The ``X-Request-ID`` header value, if available.
            Useful for correlating client-side errors with server logs.
    """

    error: str = Field(
        ...,
        description="Error type identifier (PascalCase class name)",
        examples=["ValidationError", "TaskNotFoundError"],
    )
    detail: str = Field(
        ...,
        description="Human-readable error description",
        examples=["Query must be between 1 and 500 characters."],
    )
    request_id: str | None = Field(
        default=None,
        description="Request tracking ID for log correlation",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "InvalidInputError",
                    "detail": "The provided URL is not a supported platform.",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                },
                {
                    "error": "InternalServerError",
                    "detail": "An unexpected error occurred. Please try again later.",
                    "request_id": None,
                },
            ]
        }
    }
