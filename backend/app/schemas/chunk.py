"""Paginated diagnostic responses for persisted document chunks."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.chunking.types import ChunkingStrategy


class ChunkRead(BaseModel):
    """Citation-ready chunk metadata without internal object-storage details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    page_number: int
    end_page_number: int
    section_title: str | None
    chunk_index: int
    content: str
    token_count: int
    character_count: int
    content_type: str
    chunking_strategy: ChunkingStrategy
    chunking_config_version: str
    metadata_json: dict[str, object]
    created_at: datetime


class ChunkPage(BaseModel):
    """Stable offset-paginated chunk-list response."""

    items: list[ChunkRead]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
