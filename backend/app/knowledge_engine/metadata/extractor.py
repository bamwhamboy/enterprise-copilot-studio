"""File-level metadata extraction.

Deliberately separate from the PDF parser: this handles metadata that
applies to *any* uploaded file (size, MIME type, filename), independent
of file format or content parsing.
"""

from dataclasses import dataclass

DEFAULT_MIME_TYPE = "application/octet-stream"


@dataclass(frozen=True)
class FileMetadata:
    original_filename: str
    mime_type: str
    file_size_bytes: int


def extract_file_metadata(
    *, original_filename: str, content_type: str | None, content: bytes
) -> FileMetadata:
    """Derive file-level metadata from an upload's filename, declared
    content type, and raw bytes (used only to measure size — no parsing).
    """
    return FileMetadata(
        original_filename=original_filename,
        mime_type=content_type or DEFAULT_MIME_TYPE,
        file_size_bytes=len(content),
    )
