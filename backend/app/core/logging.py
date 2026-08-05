"""Application logging configuration.

Provides a single ``configure_logging`` entry point (called once at
startup) and a ``get_logger`` helper so every module logs consistently
without each one re-configuring handlers or formatters.

Sprint 4 adds ``_ContextFilter``: every log record is automatically
enriched with the current request ID and correlation ID (see
``app.middleware.request_context`` / ``app.middleware.correlation``),
so any module can log normally and still get structured request context
"for free" — no call site needs to pass request_id/correlation_id
explicitly.
"""

import logging
import sys

from app.core.config import get_settings

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "[req=%(request_id)s corr=%(correlation_id)s] | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class _ContextFilter(logging.Filter):
    """Injects request_id/correlation_id from contextvars into every log record.

    Imports are deferred to call time (inside ``filter()``, not at
    module level) to avoid a circular import: ``middleware.request_context``
    imports ``get_logger`` from this module, so this module can't import
    from it at load time.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        from app.middleware.correlation import get_correlation_id
        from app.middleware.request_context import get_request_id

        record.request_id = get_request_id() or "-"
        record.correlation_id = get_correlation_id() or "-"
        return True


def configure_logging() -> None:
    """Configure root logging handlers and level.

    Idempotent: safe to call multiple times (e.g. once from ``main.py`` and
    once from a test fixture) without producing duplicate log lines.
    """
    settings = get_settings()
    root_logger = logging.getLogger()

    # Avoid stacking duplicate handlers if called more than once.
    root_logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handler.addFilter(_ContextFilter())

    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    # Keep noisy third-party loggers at a sane level regardless of app LOG_LEVEL.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger.

    Usage: ``logger = get_logger(__name__)`` at the top of a module.
    """
    return logging.getLogger(name)
