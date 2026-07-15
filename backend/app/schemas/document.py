"""Request metadata and responses for stored PDF documents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentRead(BaseModel):
    """Stored document metadata returned by document endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: UUID
    title: str
    authors: list[str]
    publication_year: int | None
    source_filename: str
    checksum: str
    status: DocumentStatus
    page_count: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentStatusRead(BaseModel):
    """Small polling response for asynchronous ingestion status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DocumentStatus
    error_message: str | None
    updated_at: datetime
