"""Request metadata and responses for stored PDF documents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.chunking.types import ChunkingStrategy
from app.ingestion.types import ProcessingStage
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
    chunk_count: int
    chunking_strategy: ChunkingStrategy
    processing_stage: ProcessingStage
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    error_message: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class DocumentStatusRead(BaseModel):
    """Small polling response for asynchronous ingestion status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DocumentStatus
    processing_stage: ProcessingStage
    page_count: int | None
    chunk_count: int
    chunking_strategy: ChunkingStrategy
    error_message: str | None
    error_code: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    updated_at: datetime
