"""Shared parser interface for document ingestion.

Every format-specific parser (PDF, DOCX, TXT, PPTX, CSV, XLSX, ...)
implements ``DocumentParser`` and returns a ``ParsedDocument``. This is
the one and only handoff point between "read this file" and everything
downstream: chunking, Graph RAG extraction, embedding, and Qdrant
indexing all consume ``ParsedDocument.text`` as plain text and have no
awareness of which parser produced it. Adding a new format means
adding one parser module and one ``ParserRegistry`` registration --
nothing downstream of extraction changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ParsedDocument:
    """Result of extracting a document's content as plain text.

    ``page_count`` generalizes across formats: real page count for
    PDF, slide count for PPTX, sheet count for XLSX, section/paragraph
    count for DOCX, and 1 for single-stream formats (TXT, CSV). It
    exists purely so ``Document.pages`` keeps a meaningful number
    across formats -- nothing downstream treats it as PDF-specific.
    """

    text: str
    page_count: int


@runtime_checkable
class DocumentParser(Protocol):
    """Interface every format-specific parser implements.

    ``extensions``/``mime_types`` are used by ``ParserRegistry`` to
    resolve which parser handles a given upload, and to derive the
    ingestion pipeline's allowed-extension/MIME-type sets -- so
    registering a new parser is the only step needed to make the
    upload endpoint accept its format.
    """

    extensions: frozenset[str]
    mime_types: frozenset[str]

    def extract(self, path: str | Path) -> ParsedDocument:
        """Extract plain text (and a page_count) from a file on disk.

        Deliberately synchronous everywhere this is implemented --
        every current parser library here (PyMuPDF, python-docx,
        python-pptx, openpyxl, stdlib csv) is CPU-bound and not
        async-native. Callers (the ingestion pipeline) are responsible
        for running this in a worker thread so it doesn't block the
        event loop.
        """
        ...
