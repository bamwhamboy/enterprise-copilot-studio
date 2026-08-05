"""Correlation ID propagation.

Distinct from the per-service **Request ID** (minted fresh by this
service for every request — see ``request_context.py``): the
**Correlation ID** follows a logical operation across service/process
boundaries. If an inbound request already carries one (via the
``X-Correlation-ID`` header), it's reused so a chain of calls across
future microservices shares one ID; otherwise a new one is minted here,
making this service the origin of the chain.

Stored in a ``contextvars.ContextVar`` so any code running within a
request — services, repositories, background tasks spawned from it —
can read the current correlation ID without needing the ``Request``
object threaded through every function signature.
"""

from __future__ import annotations

import contextvars
import uuid

CORRELATION_ID_HEADER = "X-Correlation-ID"

_correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> str | None:
    """Return the correlation ID for the current async context, if set."""
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token:
    """Set the correlation ID for the current async context. Returns a reset token."""
    return _correlation_id_ctx.set(correlation_id)


def reset_correlation_id(token: contextvars.Token) -> None:
    """Restore the previous correlation ID using a token from ``set_correlation_id``."""
    _correlation_id_ctx.reset(token)


def extract_or_generate(header_value: str | None) -> str:
    """Reuse an inbound ``X-Correlation-ID`` header value, or mint a new one."""
    return header_value or str(uuid.uuid4())
