"""Provider-neutral object-storage contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol


class ObjectBody(Protocol):
    """A readable response body returned by object storage."""

    def read(self, amount: int = -1) -> bytes: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class StoredObject:
    """A streamed object plus the response metadata needed by HTTP handlers."""

    body: ObjectBody
    size_bytes: int
    content_type: str
    etag: str | None = None


class ObjectStorage(Protocol):
    """Operations EvidenceGraph requires from S3-compatible storage."""

    def ensure_bucket(self) -> None:
        """Create the configured bucket if it does not already exist."""

    def upload_pdf(
        self,
        object_key: str,
        content: BinaryIO,
        *,
        size_bytes: int,
        content_type: str,
    ) -> None:
        """Write a rewindable stream under a caller-generated object key."""

    def open(self, object_key: str) -> StoredObject:
        """Open an object for streamed reading."""

    def upload_bytes(self, object_key: str, content: bytes, *, content_type: str) -> None:
        """Write a bounded generated internal artifact."""

    def delete(self, object_key: str) -> None:
        """Delete an object; deleting a missing key is successful."""
