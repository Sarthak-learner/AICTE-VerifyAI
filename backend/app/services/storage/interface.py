"""Abstract storage interface.

Keeping upload I/O behind this protocol means a future prompt can swap
in object-storage (S3, GCS) without touching the application routes.
"""
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Minimal interface required by the document ingestor."""

    def save(self, data: bytes, stored_filename: str) -> str:
        """Persist *data* under *stored_filename* and return a storage reference."""
        ...

    def exists(self, stored_filename: str) -> bool:
        """Return True if the stored file is present."""
        ...

    def delete(self, stored_filename: str) -> None:
        """Remove the stored file (used only during rollback in this phase)."""
        ...
