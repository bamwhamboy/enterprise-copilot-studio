"""Plain-text parsing.

Deliberately trivial: read the bytes, decode, done. No page concept
for a single text stream, so ``page_count`` is always 1.
"""

from pathlib import Path

from app.core.exceptions import DocumentProcessingError
from app.knowledge_engine.parser.base import ParsedDocument

# Tried in order. utf-8-sig first so a BOM (common from Windows editors)
# doesn't leak a stray character into the extracted text. latin-1 never
# raises UnicodeDecodeError (every byte value is a valid latin-1 code
# point), so it's the deliberate last-resort fallback rather than
# something that could itself fail.
_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")


class TxtParser:
    """Extracts plain text from a .txt file on disk."""

    extensions = frozenset({".txt"})
    mime_types = frozenset({"text/plain"})

    def extract(self, path: str | Path) -> ParsedDocument:
        txt_path = Path(path)

        try:
            raw = txt_path.read_bytes()
        except OSError as exc:
            raise DocumentProcessingError(f"Could not read '{txt_path.name}': {exc}") from exc

        text = None
        for encoding in _ENCODINGS:
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            # Unreachable in practice -- latin-1 above always succeeds --
            # but never silently return None from this method.
            raise DocumentProcessingError(f"Could not decode '{txt_path.name}' as text.")

        return ParsedDocument(text=text.strip(), page_count=1)
