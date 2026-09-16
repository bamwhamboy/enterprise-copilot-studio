"""DOCX parsing via python-docx.

Extracts paragraph text and table cell text, in document order.
python-docx has no notion of rendered page count (that requires an
actual layout engine), so ``page_count`` here is the document's
section count instead -- a real, cheap-to-read structural count,
clearly documented rather than a fabricated page number.
"""

from pathlib import Path

import docx

from app.core.exceptions import DocumentProcessingError
from app.knowledge_engine.parser.base import ParsedDocument


class DocxParser:
    """Extracts plain text and section count from a .docx file on disk."""

    extensions = frozenset({".docx"})
    mime_types = frozenset(
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    )

    def extract(self, path: str | Path) -> ParsedDocument:
        docx_path = Path(path)

        try:
            document = docx.Document(str(docx_path))
        except Exception as exc:  # python-docx raises its own (non-typed) errors
            raise DocumentProcessingError(
                f"Could not open '{docx_path.name}' as a DOCX file: {exc}"
            ) from exc

        parts: list[str] = []
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                parts.append(paragraph.text)

        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))

        text = "\n".join(parts).strip()
        page_count = max(len(document.sections), 1)

        return ParsedDocument(text=text, page_count=page_count)
