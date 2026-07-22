"""Uploaded document persistence model."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.chunking.types import ChunkingStrategy
from app.db.base import Base, TimestampMixin
from app.ingestion.types import ProcessingStage

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.collection import Collection


class DocumentStatus(StrEnum):
    """Valid lifecycle states for a stored document."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(TimestampMixin, Base):
    """Metadata and storage location for an uploaded PDF."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "processing_stage IN "
            "('uploaded', 'processing', 'parsing', 'chunking', 'ready', 'failed')",
            name="ck_documents_processing_stage",
        ),
        CheckConstraint(
            "chunking_strategy IN ('fixed_token', 'section_aware')",
            name="ck_documents_chunking_strategy",
        ),
        CheckConstraint("page_count IS NULL OR page_count >= 1", name="ck_documents_page_count"),
        CheckConstraint("chunk_count >= 0", name="ck_documents_chunk_count"),
        UniqueConstraint(
            "collection_id",
            "checksum",
            name="uq_documents_collection_checksum",
        ),
        Index("ix_documents_collection_id", "collection_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_processing_stage", "processing_stage"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    collection_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            native_enum=False,
            create_constraint=False,
            length=16,
            validate_strings=True,
            values_callable=lambda status_type: [status.value for status in status_type],
        ),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        server_default=DocumentStatus.UPLOADED.value,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_stage: Mapped[ProcessingStage] = mapped_column(
        Enum(
            ProcessingStage,
            name="processing_stage",
            native_enum=False,
            create_constraint=False,
            length=16,
            validate_strings=True,
            values_callable=lambda stage_type: [stage.value for stage in stage_type],
        ),
        nullable=False,
        default=ProcessingStage.UPLOADED,
        server_default=ProcessingStage.UPLOADED.value,
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    processing_attempt_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    chunking_strategy: Mapped[ChunkingStrategy] = mapped_column(
        Enum(
            ChunkingStrategy,
            name="chunking_strategy",
            native_enum=False,
            create_constraint=False,
            length=32,
            validate_strings=True,
            values_callable=lambda strategy_type: [strategy.value for strategy in strategy_type],
        ),
        nullable=False,
        default=ChunkingStrategy.SECTION_AWARE,
        server_default=ChunkingStrategy.SECTION_AWARE.value,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    parsed_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    collection: Mapped[Collection] = relationship(back_populates="documents")
    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
