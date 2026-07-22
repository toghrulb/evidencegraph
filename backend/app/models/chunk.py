"""Persisted page-aware document chunks."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.chunking.types import ChunkingStrategy
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class Chunk(Base):
    """A deterministic chunk with enough provenance for future citations."""

    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint("page_number >= 1", name="ck_chunks_page_number"),
        CheckConstraint("end_page_number >= page_number", name="ck_chunks_page_range"),
        CheckConstraint("chunk_index >= 0", name="ck_chunks_chunk_index"),
        CheckConstraint("token_count > 0", name="ck_chunks_token_count"),
        CheckConstraint("character_count > 0", name="ck_chunks_character_count"),
        CheckConstraint("length(content) > 0", name="ck_chunks_content"),
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_document_id_chunk_index", "document_id", "chunk_index", unique=True),
        Index("ix_chunks_page_number", "page_number"),
        Index("ix_chunks_chunking_strategy", "chunking_strategy"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    end_page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    chunking_strategy: Mapped[ChunkingStrategy] = mapped_column(
        String(32),
        nullable=False,
    )
    chunking_config_version: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
