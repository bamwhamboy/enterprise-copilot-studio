"""Local-disk document storage.

Responsible ONLY for saving, loading, and deleting files. Deliberately
knows nothing about PDFs, metadata extraction, or the database — a
narrow file I/O boundary so the backend (local disk today) can be
swapped for S3/Azure Blob later without touching parsing or
persistence code.
"""

import uuid
from pathlib import Path

import aiofiles

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentStorageService:
    def __init__(self, settings: Settings) -> None:
        self._base_dir = Path(settings.STORAGE_DIR)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def generate_storage_path(self, original_filename: str) -> Path:
        """Build a unique, collision-free destination path for an upload."""
        suffix = Path(original_filename).suffix or ".pdf"
        unique_name = f"{uuid.uuid4()}{suffix}"
        return self._base_dir / unique_name

    async def save_bytes(self, content: bytes, destination: Path) -> Path:
        """Write raw bytes to ``destination`` and return the path written."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(destination, "wb") as f:
            await f.write(content)
        logger.info("Saved file to %s (%d bytes)", destination, len(content))
        return destination

    async def save_text(self, text: str, storage_path: Path) -> Path:
        """Save extracted text as a sidecar ``.txt`` file next to the source file."""
        text_path = storage_path.with_suffix(".txt")
        async with aiofiles.open(text_path, "w", encoding="utf-8") as f:
            await f.write(text)
        logger.info("Saved extracted text to %s (%d chars)", text_path, len(text))
        return text_path

    async def load_bytes(self, path: str | Path) -> bytes:
        """Read a stored file's raw bytes back from disk."""
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    def delete(self, path: str | Path | None) -> None:
        """Delete a stored file if present. Safe to call with ``None`` or a missing path."""
        if not path:
            return
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted file %s", file_path)
        else:
            logger.warning("Attempted to delete missing file %s", file_path)
