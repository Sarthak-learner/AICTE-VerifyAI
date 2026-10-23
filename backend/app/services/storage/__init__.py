# Storage service package
from app.services.storage.interface import StorageBackend
from app.services.storage.local import LocalStorageBackend

__all__ = ["StorageBackend", "LocalStorageBackend"]
