"""Atomic replacement of a document's generated chunk set."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.chunking.errors import ChunkPersistenceError
from app.chunking.schemas import ChunkDraft
from app.chunking.types import ChunkingStrategy
from app.ingestion.types import ProcessingStage
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.parsing.errors import StaleProcessingAttemptError


def replace_document_chunks(
    session: Session,
    *,
    document_id: UUID,
    attempt_id: UUID,
    page_count: int,
    strategy: ChunkingStrategy,
    parsed_storage_key: str,
    drafts: list[ChunkDraft],
) -> None:
    """Replace chunks and finalize metadata in one database transaction."""
    try:
        document = session.get(Document, document_id, with_for_update=True)
        if document is None or document.processing_attempt_id != attempt_id:
            session.rollback()
            raise StaleProcessingAttemptError

        session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        session.add_all(
            Chunk(
                document_id=document_id,
                page_number=draft.page_number,
                end_page_number=draft.end_page_number,
                section_title=draft.section_title,
                chunk_index=draft.chunk_index,
                content=draft.content,
                token_count=draft.token_count,
                character_count=draft.character_count,
                content_type=draft.content_type,
                chunking_strategy=draft.chunking_strategy,
                chunking_config_version=draft.chunking_config_version,
                metadata_json=draft.metadata_json,
            )
            for draft in drafts
        )
        document.status = DocumentStatus.READY
        document.processing_stage = ProcessingStage.READY
        document.page_count = page_count
        document.chunk_count = len(drafts)
        document.chunking_strategy = strategy
        document.parsed_storage_key = parsed_storage_key
        document.error_message = None
        document.error_code = None
        document.processing_completed_at = datetime.now(tz=UTC)
        session.commit()
    except StaleProcessingAttemptError:
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        raise ChunkPersistenceError from exc
