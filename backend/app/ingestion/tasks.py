"""Celery tasks that own asynchronous ingestion status transitions."""

from __future__ import annotations

import logging
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus
from app.worker import celery_app

logger = logging.getLogger("evidencegraph.ingestion")


class IngestionClaimResult(StrEnum):
    """Outcome of attempting to claim one uploaded document."""

    CLAIMED = "claimed"
    NOT_FOUND = "not_found"
    NOT_UPLOADED = "not_uploaded"


def claim_document_for_ingestion(session: Session, document_id: UUID) -> IngestionClaimResult:
    """Atomically move an uploaded document to processing.

    The row lock makes concurrent deliveries safe. A redelivered task observes
    ``processing`` (or a terminal state) and performs no second transition.
    Phase 1 intentionally stops here; later phases own the work that may set
    ``ready`` or ``failed``.
    """
    document = session.get(Document, document_id, with_for_update=True)
    if document is None:
        session.rollback()
        return IngestionClaimResult.NOT_FOUND

    if document.status != DocumentStatus.UPLOADED:
        session.rollback()
        return IngestionClaimResult.NOT_UPLOADED

    document.status = DocumentStatus.PROCESSING
    document.error_message = None
    session.commit()
    return IngestionClaimResult.CLAIMED


@celery_app.task(  # type: ignore[untyped-decorator]
    name="evidencegraph.ingestion.start_document_ingestion",
    ignore_result=True,
    acks_late=True,
)
def start_document_ingestion(document_id: str) -> None:
    """Claim a queued document without performing any Phase 2 processing."""
    parsed_document_id = UUID(document_id)
    with SessionLocal() as session:
        result = claim_document_for_ingestion(session, parsed_document_id)

    logger.info(
        "ingestion_status_transition document_id=%s result=%s",
        parsed_document_id,
        result,
    )
