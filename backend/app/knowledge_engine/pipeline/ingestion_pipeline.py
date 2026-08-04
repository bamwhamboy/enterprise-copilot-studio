"""Document ingestion pipeline.

Split into two explicit steps rather than one bundled call, so the
service layer can persist a real ``UPLOADED`` row right after the file
is saved, then transition through ``PROCESSING`` to ``READY``/``FAILED``
around the parse step — a meaningful state machine even though
everything here runs synchronously within one request.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import FileTooLargeError, UnsupportedMediaTypeError
from app.core.logging import get_logger
from app.knowledge_engine.metadata.extractor import FileMetadata, extract_file_metadata
from app.knowledge_engine.parser.pdf_parser import ParsedPdf, PdfParser
from app.knowledge_engine.storage.document_storage import DocumentStorageService

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf"}


@dataclass(frozen=True)
class SavedUpload:
    storage_path: Path
    file_metadata: FileMetadata


@dataclass(frozen=True)
class ParsedUpload:
    parsed: ParsedPdf
    extracted_text_path: Path


class DocumentIngestionPipeline:
    def __init__(self, settings: Settings, storage: DocumentStorageService) -> None:
        self._settings = settings
        self._storage = storage
        self._parser = PdfParser()

    def _validate(self, *, filename: str, content_type: str | None, size_bytes: int) -> None:
        extension = Path(filename).suffix.lower()
        mime_ok = content_type is None or content_type in ALLOWED_MIME_TYPES
        if extension not in ALLOWED_EXTENSIONS or not mime_ok:
            raise UnsupportedMediaTypeError(
                f"Unsupported file type '{content_type or extension}'. "
                "Only PDF documents are supported."
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
        """Parse a previously-saved PDF and persist its extracted text.

        PyMuPDF is CPU-bound and not async-native, so extraction runs in
        a worker thread rather than blocking the event loop.
        """
        logger.info("Parsing %s", storage_path)
        parsed = await asyncio.to_thread(self._parser.extract, storage_path)
        extracted_text_path = await self._storage.save_text(parsed.text, storage_path)
        return ParsedUpload(parsed=parsed, extracted_text_path=extracted_text_path)
