"""Stored-PDF existence, size, and signature validation."""

from __future__ import annotations

from app.documents.validation import PDF_SIGNATURE
from app.parsing.errors import (
    InvalidStoredPdfSignatureError,
    StoredPdfMissingError,
    StoredPdfReadError,
    StoredPdfTooLargeError,
)
from app.storage.base import ObjectStorage
from app.storage.s3 import ObjectNotFoundError, StorageError

READ_SIZE_BYTES = 64 * 1024


def load_stored_pdf(
    storage: ObjectStorage,
    storage_key: str,
    *,
    max_size_bytes: int,
) -> bytes:
    """Load a bounded stored PDF and independently verify its signature."""
    try:
        stored = storage.open(storage_key)
    except ObjectNotFoundError as exc:
        raise StoredPdfMissingError from exc
    except StorageError as exc:
        raise StoredPdfReadError from exc

    try:
        if stored.size_bytes > max_size_bytes:
            raise StoredPdfTooLargeError

        chunks: list[bytes] = []
        size_bytes = 0
        while chunk := stored.body.read(READ_SIZE_BYTES):
            size_bytes += len(chunk)
            if size_bytes > max_size_bytes:
                raise StoredPdfTooLargeError
            chunks.append(chunk)
    except (StoredPdfTooLargeError, InvalidStoredPdfSignatureError):
        raise
    except Exception as exc:
        raise StoredPdfReadError from exc
    finally:
        stored.body.close()

    pdf_bytes = b"".join(chunks)
    if not pdf_bytes.startswith(PDF_SIGNATURE):
        raise InvalidStoredPdfSignatureError
    return pdf_bytes
