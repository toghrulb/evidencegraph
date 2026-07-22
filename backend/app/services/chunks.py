"""Read-only diagnostic access to one document's persisted chunks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.services.documents import get_document


def list_document_chunks(
    session: Session,
    document_id: UUID,
    *,
    offset: int,
    limit: int,
) -> tuple[list[Chunk], int]:
    """Return source-ordered chunks after verifying the document exists."""
    get_document(session, document_id)
    total = session.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    )
    statement = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement)), int(total or 0)
