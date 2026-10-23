"""Local filesystem storage backend.

Files are written to the configured upload directory using a server-side
random UUID name so the original filename is never used as the storage path.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalStorageBackend:
    """Stores files on the local filesystem outside the web-server root."""

    def __init__(self, upload_dir: str) -> None:
        self._root = Path(upload_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorageBackend root: %s", self._root)

    def save(self, data: bytes, stored_filename: str) -> str:
        """Write *data* to *stored_filename* and return the relative reference."""
        dest = self._root / stored_filename
        dest.write_bytes(data)
        logger.debug("Stored %d bytes → %s", len(data), dest)
        return stored_filename  # The storage reference is the UUID-based name only

    def exists(self, stored_filename: str) -> bool:
        return (self._root / stored_filename).is_file()

    def delete(self, stored_filename: str) -> None:
        """Delete a file — only used for rollback when DB commit fails."""
        path = self._root / stored_filename
        if path.exists():
            path.unlink()
            logger.warning("Rolled back: deleted %s", path)
