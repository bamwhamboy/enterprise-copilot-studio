"""Application entrypoint.

Defines a ``create_app`` factory (so tests can build isolated app
instances) and exposes the module-level ``app`` object that
Uvicorn/Docker actually serve.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    DocumentProcessingError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedMediaTypeError,
)
from app.core.logging import configure_logging, get_logger
from app.database.session import AsyncSessionLocal, dispose_engine
from app.guardrails.guardrails_runtime import GuardrailViolationError
from app.knowledge_engine.indexing.indexing_service import DocumentNotReadyError
from app.middleware.request_context import RequestContextMiddleware
from app.repositories.document_repository import DocumentRepository
from app.services.auth_service import AuthenticationError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup/shutdown hooks.

    Startup now does one deliberate, narrowly-scoped database write: see
    _reset_stale_indexing_documents below. Everything else about
    startup is unchanged -- no other database, Redis, or Qdrant
    integration happens here.
    """
    settings = get_settings()
    logger.info("Starting %s [env=%s]", settings.APP_NAME, settings.APP_ENV)

    await _reset_stale_indexing_documents()

    yield

    logger.info("Shutting down %s", settings.APP_NAME)
    await dispose_engine()


async def _reset_stale_indexing_documents() -> None:
    """Recover documents left stuck at index_status="INDEXING" by a
    previous process that died mid-index (see
    DocumentRepository.reset_stale_indexing's docstring for why this is
    always safe and always correct to do on every startup, not just
    after a suspected crash).
    """
    try:
        async with AsyncSessionLocal() as session:
            count = await DocumentRepository(session).reset_stale_indexing()
        if count:
            logger.warning(
                "Reset %d document(s) stuck at index_status=INDEXING to FAILED "
                "(leftover from a process that didn't shut down cleanly, e.g. "
                "an out-of-memory kill while loading the embedding model).",
                count,
            )
    except Exception:
        # Never let this best-effort cleanup step prevent the app from
        # starting -- if the database isn't reachable yet, the app's
        # normal request-time error handling will surface that clearly
        # anyway.
        logger.exception("Failed to reset stale INDEXING documents at startup")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnsupportedMediaTypeError)
    async def unsupported_media_type_handler(
        request: Request, exc: UnsupportedMediaTypeError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(FileTooLargeError)
    async def file_too_large_handler(request: Request, exc: FileTooLargeError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DocumentProcessingError)
    async def document_processing_error_handler(
        request: Request, exc: DocumentProcessingError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DocumentNotReadyError)
    async def document_not_ready_handler(
        request: Request, exc: DocumentNotReadyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(GuardrailViolationError)
    async def guardrail_violation_handler(
        request: Request, exc: GuardrailViolationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": str(exc),
                "stage": exc.stage,
                "issues": [issue.message for issue in exc.result.issues],
            },
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    app.include_router(api_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
