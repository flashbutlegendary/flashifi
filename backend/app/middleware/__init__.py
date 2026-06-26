"""Application middleware for the FlashiFi API.

This package provides ASGI middleware components that are registered on
the FastAPI application during startup:

- :class:`RequestIDMiddleware`: Assigns or propagates a unique request ID.
- :class:`LoggingMiddleware`: Structured access logging with timing.

Usage::

    from app.middleware import RequestIDMiddleware, LoggingMiddleware

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
"""

from app.middleware.request_id import RequestIDMiddleware
from app.middleware.logging_mw import LoggingMiddleware

__all__: list[str] = [
    "RequestIDMiddleware",
    "LoggingMiddleware",
]
