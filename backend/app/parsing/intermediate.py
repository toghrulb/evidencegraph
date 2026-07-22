"""Versioned parsed-document persistence in object storage."""

from __future__ import annotations

from uuid import UUID

from app.parsing.errors import ParsedIntermediateStorageError
from app.parsing.schemas import PARSED_DOCUMENT_SCHEMA_VERSION, ParsedDocument
from app.storage.base import ObjectStorage
from app.storage.s3 import StorageError

PARSED_DOCUMENT_CONTENT_TYPE = "application/vnd.evidencegraph.parsed+json"


def parsed_document_key(collection_id: UUID, document_id: UUID) -> str:
    """Return a stable generated key whose content carries explicit versions."""
    return (
        f"collections/{collection_id}/documents/{document_id}/"
        f"parsed-schema-{PARSED_DOCUMENT_SCHEMA_VERSION}.json"
    )


def store_parsed_document(
    storage: ObjectStorage,
    object_key: str,
    parsed_document: ParsedDocument,
) -> None:
    """Serialize and store one complete immutable parser result."""
    content = parsed_document.model_dump_json().encode("utf-8")
    try:
        storage.upload_bytes(
            object_key,
            content,
            content_type=PARSED_DOCUMENT_CONTENT_TYPE,
        )
    except StorageError as exc:
        raise ParsedIntermediateStorageError from exc
