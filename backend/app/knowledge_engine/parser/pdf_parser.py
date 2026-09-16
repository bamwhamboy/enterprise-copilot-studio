"""PDF parsing via PyMuPDF (fitz).

Extraction only — returns full text and page count, nothing more. No
chunking, no embeddings (explicitly out of scope for this sprint).

Deliberately synchronous: PyMuPDF is CPU-bound and not async-native.
Callers (the ingestion pipeline) are responsible for running this in a
worker thread so it doesn't block the event loop.
"""

from pathlib import Path

import fitz  # PyMuPDF

from app.core.exceptions import DocumentProcessingError
from app.core.logging import get_logger
from app.knowledge_engine.parser.base import ParsedDocument

logger = get_logger(__name__)


class PdfParser:
    """Extracts plain text and page count from a PDF file on disk."""

    extensions = frozenset({".pdf"})
    mime_types = frozenset({"application/pdf"})

    def extract(self, path: str | Path) -> ParsedDocument:
        pdf_path = Path(path)

        try:
            document = fitz.open(pdf_path)
        except Exception as exc:  # PyMuPDF raises its own (non-typed) errors
            raise DocumentProcessingError(
                f"Could not open '{pdf_path.name}' as a PDF: {exc}"
            ) from exc

        try:
            if document.page_count == 0:
                raise DocumentProcessingError(f"'{pdf_path.name}' has no pages.")

            page_texts = [page.get_text() for page in document]
            text = "\n\n".join(page_texts).strip()

            if not text:
                logger.warning(
                    "No extractable text in %s (%d pages) — likely a scanned/image PDF",
                    pdf_path.name,
                    document.page_count,
                )

            return ParsedDocument(text=text, page_count=document.page_count)
        finally:
            document.close()
