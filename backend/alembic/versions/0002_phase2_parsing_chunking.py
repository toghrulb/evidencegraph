"""Add Phase 2 processing metadata and chunks.

Revision ID: 0002_phase2
Revises: 0001_phase1
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_phase2"
down_revision: str | None = "0001_phase1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add detailed processing state and citation-ready chunk storage."""
    op.add_column("documents", sa.Column("error_code", sa.String(length=64), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "processing_stage",
            sa.String(length=16),
            server_default=sa.text("'uploaded'"),
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("processing_attempt_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "chunking_strategy",
            sa.String(length=32),
            server_default=sa.text("'section_aware'"),
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("parsed_storage_key", sa.String(length=1024), nullable=True),
    )
    op.execute(
        """
        UPDATE documents
        SET processing_stage = CASE status
            WHEN 'processing' THEN 'processing'
            WHEN 'ready' THEN 'ready'
            WHEN 'failed' THEN 'failed'
            ELSE 'uploaded'
        END
        """
    )
    op.create_check_constraint(
        "ck_documents_processing_stage",
        "documents",
        "processing_stage IN ('uploaded', 'processing', 'parsing', 'chunking', 'ready', 'failed')",
    )
    op.create_check_constraint(
        "ck_documents_chunking_strategy",
        "documents",
        "chunking_strategy IN ('fixed_token', 'section_aware')",
    )
    op.create_check_constraint(
        "ck_documents_page_count",
        "documents",
        "page_count IS NULL OR page_count >= 1",
    )
    op.create_check_constraint("ck_documents_chunk_count", "documents", "chunk_count >= 0")
    op.create_index("ix_documents_processing_stage", "documents", ["processing_stage"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("end_page_number", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.String(length=500), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("chunking_strategy", sa.String(length=32), nullable=False),
        sa.Column("chunking_config_version", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("page_number >= 1", name="ck_chunks_page_number"),
        sa.CheckConstraint(
            "end_page_number >= page_number",
            name="ck_chunks_page_range",
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_chunks_chunk_index"),
        sa.CheckConstraint("token_count > 0", name="ck_chunks_token_count"),
        sa.CheckConstraint("character_count > 0", name="ck_chunks_character_count"),
        sa.CheckConstraint("length(content) > 0", name="ck_chunks_content"),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index(
        "ix_chunks_document_id_chunk_index",
        "chunks",
        ["document_id", "chunk_index"],
        unique=True,
    )
    op.create_index("ix_chunks_page_number", "chunks", ["page_number"])
    op.create_index("ix_chunks_chunking_strategy", "chunks", ["chunking_strategy"])


def downgrade() -> None:
    """Remove Phase 2 chunks and processing metadata."""
    op.drop_index("ix_chunks_chunking_strategy", table_name="chunks")
    op.drop_index("ix_chunks_page_number", table_name="chunks")
    op.drop_index("ix_chunks_document_id_chunk_index", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_documents_processing_stage", table_name="documents")
    op.drop_constraint("ck_documents_chunk_count", "documents", type_="check")
    op.drop_constraint("ck_documents_page_count", "documents", type_="check")
    op.drop_constraint("ck_documents_chunking_strategy", "documents", type_="check")
    op.drop_constraint("ck_documents_processing_stage", "documents", type_="check")
    op.drop_column("documents", "parsed_storage_key")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "chunking_strategy")
    op.drop_column("documents", "processing_attempt_id")
    op.drop_column("documents", "processing_completed_at")
    op.drop_column("documents", "processing_started_at")
    op.drop_column("documents", "processing_stage")
    op.drop_column("documents", "error_code")
