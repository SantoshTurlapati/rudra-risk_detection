import logging
import os
import re
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.core.config import settings
from app.ai.image_validation import MAX_IMAGE_BYTES, validate_image_bytes

logger = logging.getLogger(__name__)
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_-]+$")
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9_-]+\.(?:png|jpg|webp)$")


class StorageUnavailable(RuntimeError):
    """Raised when the configured private object store is not available."""


class PrivateImageStorage(Protocol):
    def put(self, key: str, data: bytes, media_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


def validate_storage_key(key: str) -> tuple[str, ...]:
    path = PurePosixPath(key)
    parts = path.parts
    if (
        not key
        or "\\" in key
        or "\x00" in key
        or path.is_absolute()
        or len(parts) != 3
        or any(part in {"", ".", ".."} for part in parts)
        or not _SAFE_SEGMENT.fullmatch(parts[0])
        or not _SAFE_SEGMENT.fullmatch(parts[1])
        or not _SAFE_FILENAME.fullmatch(parts[2])
    ):
        raise ValueError("Unsafe private image storage key.")
    return parts


class UnconfiguredPrivateImageStorage:
    def __init__(self, reason: str = (
        "Private brand image storage is not configured. "
        "Configure a durable private storage adapter."
    )):
        self.reason = reason

    def _unavailable(self) -> None:
        raise StorageUnavailable(self.reason)

    def put(self, key: str, data: bytes, media_type: str) -> None:
        self._unavailable()

    def get(self, key: str) -> bytes:
        self._unavailable()

    def delete(self, key: str) -> None:
        self._unavailable()


class LocalPrivateImageStorage:
    """Private filesystem adapter; durability requires an operator-managed persistent mount."""

    def __init__(self, root: str):
        if not root:
            raise ValueError("A private image storage directory must be configured.")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            logger.warning("Could not restrict private image storage directory permissions")

    def _path(self, key: str) -> Path:
        parts = validate_storage_key(key)
        path = self.root.joinpath(*parts).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Unsafe private image storage key.")
        return path

    def put(self, key: str, data: bytes, media_type: str) -> None:
        image = validate_image_bytes(data)
        if image.media_type != media_type:
            raise ValueError("Stored image media type does not match its decoded content.")
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.parent.chmod(0o700)
        except OSError:
            logger.warning("Could not restrict private image object directory permissions")
        temporary = path.with_name(f".{path.name}.{os.urandom(8).hex()}.tmp")
        try:
            with temporary.open("xb") as output:
                output.write(data)
            try:
                temporary.chmod(0o600)
            except OSError:
                logger.warning("Could not restrict private image object permissions")
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError("Stored image exceeds the supported size limit.")
        with path.open("rb") as image:
            data = image.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("Stored image exceeds the supported size limit.")
        return data

    def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            path.unlink()
        except FileNotFoundError:
            return


def get_private_image_storage() -> PrivateImageStorage:
    backend = settings.BRAND_IMAGE_STORAGE_BACKEND.casefold()
    if backend == "local" and settings.BRAND_IMAGE_STORAGE_DIR:
        try:
            return LocalPrivateImageStorage(settings.BRAND_IMAGE_STORAGE_DIR)
        except (OSError, ValueError):
            logger.exception("Configured private image storage is unavailable")
            return UnconfiguredPrivateImageStorage(
                "Configured private image storage directory is unavailable."
            )
    if backend == "local":
        return UnconfiguredPrivateImageStorage(
            "Local private image storage requires BRAND_IMAGE_STORAGE_DIR."
        )
    if backend not in {"disabled", "local"}:
        logger.error("Unsupported brand image storage backend configured: %s", backend)
        return UnconfiguredPrivateImageStorage(
            "Configured private image storage backend is unsupported."
        )
    return UnconfiguredPrivateImageStorage()


def get_brand_image_storage() -> PrivateImageStorage:
    """FastAPI dependency; tests and deployments can override the adapter."""
    return get_private_image_storage()
