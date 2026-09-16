"""Resolves which ``DocumentParser`` handles a given upload.

The registry is also the single source of truth for "what formats
does ingestion currently accept" -- ``allowed_extensions()`` and
``allowed_mime_types()`` are derived from whatever parsers are
registered, so the ingestion pipeline's validation gate never needs
its own separate, hand-maintained list that could drift out of sync
with what parsers actually exist.
"""

from __future__ import annotations

from pathlib import Path

from app.knowledge_engine.parser.base import DocumentParser


class ParserRegistry:
    def __init__(self, parsers: list[DocumentParser]) -> None:
        self._by_extension: dict[str, DocumentParser] = {}
        for parser in parsers:
            for extension in parser.extensions:
                self._by_extension[extension] = parser
        self._parsers = list(parsers)

    def allowed_extensions(self) -> frozenset[str]:
        return frozenset(self._by_extension.keys())

    def allowed_mime_types(self) -> frozenset[str]:
        mime_types: set[str] = set()
        for parser in self._parsers:
            mime_types.update(parser.mime_types)
        return frozenset(mime_types)

    def resolve(self, filename: str) -> DocumentParser | None:
        """Returns the parser registered for ``filename``'s extension,
        or ``None`` if no parser is registered for it. Resolution is by
        extension only -- MIME type is used for validation (see the
        ingestion pipeline), not for parser selection, since a
        mismatched-but-plausible Content-Type header shouldn't change
        which parser actually opens the file.
        """
        extension = Path(filename).suffix.lower()
        return self._by_extension.get(extension)


def build_default_registry() -> ParserRegistry:
    """Constructs the registry with every parser this sprint supports.

    Imports are local to this function (not module-level) so that
    importing ``app.knowledge_engine.parser.registry`` doesn't force
    every parser's own dependency (PyMuPDF, python-docx, python-pptx,
    openpyxl) to import unless a registry is actually built -- mirrors
    the lazy-import discipline already used for the LLM
    gateway/litellm in ``app/core/dependencies.py``.
    """
    from app.knowledge_engine.parser.csv_parser import CsvParser
    from app.knowledge_engine.parser.docx_parser import DocxParser
    from app.knowledge_engine.parser.pdf_parser import PdfParser
    from app.knowledge_engine.parser.pptx_parser import PptxParser
    from app.knowledge_engine.parser.txt_parser import TxtParser
    from app.knowledge_engine.parser.xlsx_parser import XlsxParser

    return ParserRegistry(
        [
            PdfParser(),
            DocxParser(),
            TxtParser(),
            PptxParser(),
            CsvParser(),
            XlsxParser(),
        ]
    )
