"""Document ingestion pipeline.

Split into two explicit steps rather than one bundled call, so the
service layer can persist a real ``UPLOADED`` row right after the file
is saved, then transition through ``PROCESSING`` to ``READY``/``FAILED``
around the parse step — a meaningful state machine even though
everything here runs synchronously within one request.

Format dispatch is entirely delegated to ``ParserRegistry`` -- this
pipeline has no format-specific logic of its own and no longer
hardcodes PDF. Adding a new supported format means adding a parser and
registering it; nothing here changes.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import (
    DocumentProcessingError,
    FileTooLargeError,
    UnsupportedMediaTypeError,
)
from app.core.logging import get_logger
from app.knowledge_engine.metadata.extractor import FileMetadata, extract_file_metadata
from app.knowledge_engine.parser.base import ParsedDocument
from app.knowledge_engine.parser.registry import ParserRegistry, build_default_registry
from app.knowledge_engine.storage.document_storage import DocumentStorageService

logger = get_logger(__name__)


@dataclass(frozen=True)
class SavedUpload:
    storage_path: Path
    file_metadata: FileMetadata


@dataclass(frozen=True)
class ParsedUpload:
    parsed: ParsedDocument
    extracted_text_path: Path


class DocumentIngestionPipeline:
    def __init__(
        self,
        settings: Settings,
        storage: DocumentStorageService,
        registry: ParserRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._storage = storage
        # Injectable for tests; defaults to every format this sprint
        # supports (see build_default_registry's own lazy imports).
        self._registry = registry if registry is not None else build_default_registry()

    def _validate(self, *, filename: str, content_type: str | None, size_bytes: int) -> None:
        extension = Path(filename).suffix.lower()
        allowed_extensions = self._registry.allowed_extensions()
        allowed_mime_types = self._registry.allowed_mime_types()

        mime_ok = content_type is None or content_type in allowed_mime_types
        if extension not in allowed_extensions or not mime_ok:
            supported = ", ".join(sorted(allowed_extensions))
            raise UnsupportedMediaTypeError(
                f"Unsupported file type '{content_type or extension}'. "
                f"Supported formats: {supported}."
            )

        max_bytes = self._settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise FileTooLargeError(
                f"File is {size_bytes / (1024 * 1024):.1f}MB, which exceeds the "
                f"{self._settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )

    async def save_upload(
        self, *, filename: str, content_type: str | None, content: bytes
    ) -> SavedUpload:
        """Validate and persist the raw upload to storage. No parsing yet."""
        self._validate(filename=filename, content_type=content_type, size_bytes=len(content))

        file_metadata = extract_file_metadata(
            original_filename=filename, content_type=content_type, content=content
        )
        destination = self._storage.generate_storage_path(filename)
        storage_path = await self._storage.save_bytes(content, destination)

        return SavedUpload(storage_path=storage_path, file_metadata=file_metadata)

    async def parse_and_store_text(self, storage_path: Path) -> ParsedUpload:
        """Parse a previously-saved upload and persist its extracted text.

        The parser is resolved from ``storage_path``'s own extension --
        that extension came from the original filename via
        ``generate_storage_path``, and already passed ``_validate``, so
        a matching parser is guaranteed to be registered.

        Every current parser library (PyMuPDF, python-docx,
        python-pptx, openpyxl, stdlib csv) is CPU-bound and not
        async-native, so extraction runs in a worker thread rather than
        blocking the event loop.
        """
        parser = self._registry.resolve(storage_path.name)
        if parser is None:
            # Defensive only -- _validate already rejects anything
            # without a registered parser before a file ever reaches
            # storage, so this should be unreachable in practice.
            raise DocumentProcessingError(
                f"No parser registered for '{storage_path.name}'."
            )

        logger.info("Parsing %s with %s", storage_path, type(parser).__name__)
        parsed = await asyncio.to_thread(parser.extract, storage_path)
        extracted_text_path = await self._storage.save_text(parsed.text, storage_path)
        return ParsedUpload(parsed=parsed, extracted_text_path=extracted_text_path)
