"""Celery task entry points for asynchronous document processing."""

from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.orchestrator import process_document
from app.storage.factory import storage_from_settings
from app.worker import celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    name="evidencegraph.ingestion.start_document_ingestion",
    ignore_result=True,
    acks_late=True,
)
def start_document_ingestion(document_id: str) -> None:
    """Run the retry-safe Phase 2 parser and chunker for one stored PDF."""
    settings = get_settings()
    process_document(
        SessionLocal,
        storage_from_settings(settings),
        settings,
        UUID(document_id),
        job_id=_current_job_id(),
    )


def _current_job_id() -> str | None:
    """Read Celery's delivery identifier without coupling the orchestrator to Celery."""
    request = getattr(start_document_ingestion, "request", None)
    value = getattr(request, "id", None)
    return str(value) if value is not None else None
