"""CSV parsing via the stdlib csv module.

Tabular data has no natural prose form, and the downstream chunker is
purely token-based -- it will split a serialized table at an arbitrary
row boundary with no idea it was ever a table. If a row were rendered
as bare values, a chunk boundary landing mid-table would silently
orphan data from its column names. To survive that, every row is
serialized on its own line with its column names repeated inline
(``Column: value | Column: value``), so any chunk that contains a row
at all contains everything needed to understand it -- no dependency on
which chunk the header ended up in.

``page_count`` is always 1: a CSV is a single stream, not paginated.
"""

import csv
from itertools import zip_longest
from pathlib import Path

from app.core.exceptions import DocumentProcessingError
from app.knowledge_engine.parser.base import ParsedDocument

_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")


def _serialize_row(headers: list[str], row: list[str]) -> str:
    pairs = [
        f"{header}: {value}"
        for header, value in zip_longest(headers, row, fillvalue="")
        if header or value
    ]
    return " | ".join(pairs)


class CsvParser:
    """Extracts row-serialized text from a .csv file on disk."""

    extensions = frozenset({".csv"})
    mime_types = frozenset({"text/csv"})

    def extract(self, path: str | Path) -> ParsedDocument:
        csv_path = Path(path)

        try:
            raw = csv_path.read_bytes()
        except OSError as exc:
            raise DocumentProcessingError(f"Could not read '{csv_path.name}': {exc}") from exc

        decoded = None
        for encoding in _ENCODINGS:
            try:
                decoded = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if decoded is None:
            raise DocumentProcessingError(f"Could not decode '{csv_path.name}' as text.")

        try:
            rows = list(csv.reader(decoded.splitlines()))
        except csv.Error as exc:
            raise DocumentProcessingError(f"Could not parse '{csv_path.name}' as CSV: {exc}") from exc

        if not rows:
            return ParsedDocument(text="", page_count=1)

        headers = rows[0]
        # Header-only or entirely-blank-rows CSVs still parse cleanly to
        # empty text rather than raising -- an empty knowledge source
        # document is a valid (if unhelpful) outcome, not an error.
        lines = [
            _serialize_row(headers, row)
            for row in rows[1:]
            if any(cell.strip() for cell in row)
        ]

        return ParsedDocument(text="\n".join(lines).strip(), page_count=1)
