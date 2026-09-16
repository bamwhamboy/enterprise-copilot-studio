"""PPTX parsing via python-pptx.

Extracts text from every text frame on every slide, in slide order.
``page_count`` is the actual slide count -- unlike DOCX, this is a
real, exact number for PPTX.
"""

from pathlib import Path

import pptx

from app.core.exceptions import DocumentProcessingError
from app.knowledge_engine.parser.base import ParsedDocument


class PptxParser:
    """Extracts plain text and slide count from a .pptx file on disk."""

    extensions = frozenset({".pptx"})
    mime_types = frozenset(
        {"application/vnd.openxmlformats-officedocument.presentationml.presentation"}
    )

    def extract(self, path: str | Path) -> ParsedDocument:
        pptx_path = Path(path)

        try:
            presentation = pptx.Presentation(str(pptx_path))
        except Exception as exc:  # python-pptx raises its own (non-typed) errors
            raise DocumentProcessingError(
                f"Could not open '{pptx_path.name}' as a PPTX file: {exc}"
            ) from exc

        slide_texts: list[str] = []
        for slide_number, slide in enumerate(presentation.slides, start=1):
            frame_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text_frame.text.strip():
                    frame_texts.append(shape.text_frame.text.strip())
            if frame_texts:
                slide_texts.append(f"Slide {slide_number}:\n" + "\n".join(frame_texts))

        text = "\n\n".join(slide_texts).strip()
        page_count = len(presentation.slides)

        return ParsedDocument(text=text, page_count=page_count)
