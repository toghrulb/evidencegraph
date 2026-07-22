"""Original-document persistence and lifecycle operations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.chunking.types import ChunkingStrategy
from app.documents.validation import ValidatedPdf
from app.ingestion.dispatcher import IngestionDispatcher
from app.ingestion.types import ProcessingStage
from app.models.collection import Collection
from app.models.document import Document, DocumentStatus
from app.storage.base import ObjectStorage, StoredObject
from app.storage.s3 import StorageError

logger = logging.getLogger("evidencegraph.documents")


class DocumentNotFoundError(LookupError):
    """Raised when a document identifier does not exist."""


class DocumentCollectionNotFoundError(LookupError):
    """Raised when an upload targets a missing collection."""


class DuplicateDocumentError(ValueError):
    """Raised when the same PDF already exists in a collection."""


def list_documents(session: Session, collection_id: UUID) -> list[Document]:
    """Return documents in a collection after verifying the collection exists."""
    _require_collection(session, collection_id)
    statement = (
        select(Document)
        .where(Document.collection_id == collection_id)
        .order_by(Document.created_at.desc(), Document.id)
    )
    return list(session.scalars(statement))


def get_document(session: Session, document_id: UUID) -> Document:
    """Return one document or raise a controlled not-found error."""
    document = session.get(Document, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Document {document_id} does not exist.")
    return document


def create_document(
    session: Session,
    storage: ObjectStorage,
    dispatcher: IngestionDispatcher,
    *,
    collection_id: UUID,
    upload: ValidatedPdf,
    title: str | None,
    authors: list[str] | None,
    publication_year: int | None,
    chunking_strategy: ChunkingStrategy,
) -> Document:
    """Store a validated PDF, persist metadata, and enqueue ingestion."""
    _require_collection(session, collection_id, lock_for_update=True)
    duplicate = session.scalar(
        select(Document.id).where(
            Document.collection_id == collection_id,
            Document.checksum == upload.checksum,
        )
    )
    if duplicate is not None:
        raise DuplicateDocumentError("This PDF already exists in the collection.")

    document_id = uuid4()
    storage_key = f"collections/{collection_id}/documents/{document_id}.pdf"
    normalized_title = _normalize_title(title, upload.source_filename)
    normalized_authors = _normalize_authors(authors)
    document = Document(
        id=document_id,
        collection_id=collection_id,
        title=normalized_title,
        authors=normalized_authors,
        publication_year=publication_year,
        source_filename=upload.source_filename,
        storage_key=storage_key,
        checksum=upload.checksum,
        status=DocumentStatus.UPLOADED,
        chunking_strategy=chunking_strategy,
    )

    storage.ensure_bucket()
    try:
        storage.upload_pdf(
            storage_key,
            cast(BinaryIO, upload.file),
            size_bytes=upload.size_bytes,
            content_type=upload.content_type,
        )
    except StorageError:
        _cleanup_failed_upload(storage, storage_key)
        raise
    session.add(document)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _cleanup_failed_upload(storage, storage_key)
        duplicate = session.scalar(
            select(Document.id).where(
                Document.collection_id == collection_id,
                Document.checksum == upload.checksum,
            )
        )
        if duplicate is not None:
            raise DuplicateDocumentError("This PDF already exists in the collection.") from exc
        raise
    except SQLAlchemyError:
        session.rollback()
        _cleanup_failed_upload(storage, storage_key)
        raise

    try:
        dispatcher.enqueue(document.id)
    except Exception:
        logger.exception("ingestion_dispatch_failed document_id=%s", document.id)
        document.status = DocumentStatus.FAILED
        document.processing_stage = ProcessingStage.FAILED
        document.error_message = "The ingestion job could not be queued."
        document.error_code = "ingestion_dispatch_failed"
        document.processing_completed_at = datetime.now(tz=UTC)
        session.commit()

    session.refresh(document)
    return document


def open_document(session: Session, storage: ObjectStorage, document_id: UUID) -> StoredObject:
    """Open the original stored PDF for streamed download."""
    document = get_document(session, document_id)
    return storage.open(document.storage_key)


def delete_document(session: Session, storage: ObjectStorage, document_id: UUID) -> None:
    """Delete both the stored PDF and its metadata."""
    document = get_document(session, document_id)
    storage.delete(document.storage_key)
    if document.parsed_storage_key is not None:
        storage.delete(document.parsed_storage_key)
    session.delete(document)
    session.commit()


def _require_collection(
    session: Session,
    collection_id: UUID,
    *,
    lock_for_update: bool = False,
) -> None:
    statement = select(Collection.id).where(Collection.id == collection_id)
    if lock_for_update:
        statement = statement.with_for_update()
    if session.scalar(statement) is None:
        raise DocumentCollectionNotFoundError(f"Collection {collection_id} does not exist.")


def _normalize_title(title: str | None, source_filename: str) -> str:
    fallback = Path(source_filename).stem
    normalized = (title or fallback).strip()
    if not normalized:
        normalized = fallback
    return normalized[:500]


def _normalize_authors(authors: list[str] | None) -> list[str]:
    if authors is None:
        return []
    return [normalized for author in authors if (normalized := author.strip())]


def _cleanup_failed_upload(storage: ObjectStorage, storage_key: str) -> None:
    try:
        storage.delete(storage_key)
    except StorageError:
        logger.exception("failed_upload_cleanup_failed storage_key=%s", storage_key)
