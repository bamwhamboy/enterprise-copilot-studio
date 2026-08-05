"""Request context middleware.

Assigns a unique request ID to every incoming request, exposes it on the
response as ``X-Request-ID``, and logs a single structured line per
request with method, path, status code, and duration. This is generic
observability plumbing — it has no knowledge of AI/business logic.

Sprint 4 extends this (without changing the above): the request ID is
now also stored in a ``contextvars.ContextVar`` (see ``get_request_id``)
so any code running within the request can read it without needing the
``Request`` object, and the middleware now also resolves/propagates a
Correlation ID (see ``correlation.py``) via ``X-Correlation-ID``.
"""

import contextvars
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.middleware.correlation import (
    CORRELATION_ID_HEADER,
    extract_or_generate,
    reset_correlation_id,
    set_correlation_id,
)

logger = get_logger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"

_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Return the request ID for the current async context, if set."""
    return _request_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID + correlation ID and log basic request/response metadata."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request_id_token = _request_id_ctx.set(request_id)

        correlation_id = extract_or_generate(request.headers.get(CORRELATION_ID_HEADER))
        request.state.correlation_id = correlation_id
        correlation_id_token = set_correlation_id(correlation_id)

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            logger.info(
                "%s %s -> %s (%.2fms) [request_id=%s]",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request_id,
            )

            return response
        finally:
            # Reset after logging so a logging filter reading these
            # contextvars (see core/logging.py) sees them for this
            # request's own log line, not the previous request's.
            _request_id_ctx.reset(request_id_token)
            reset_correlation_id(correlation_id_token)
