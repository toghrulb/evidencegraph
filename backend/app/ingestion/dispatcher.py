"""Queue-dispatch abstraction for document ingestion."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast
from uuid import UUID

from app.ingestion.tasks import start_document_ingestion


class IngestionDispatcher(Protocol):
    """Submit a document to the asynchronous ingestion queue."""

    def enqueue(self, document_id: UUID) -> None:
        """Queue one document for ingestion."""


class CeleryIngestionDispatcher:
    """Dispatch ingestion work through Celery without exposing Celery to API code."""

    def __init__(self, enqueue_task: Callable[[str], object] | None = None) -> None:
        self._enqueue_task = enqueue_task or cast(
            Callable[[str], object], start_document_ingestion.delay
        )

    def enqueue(self, document_id: UUID) -> None:
        """Serialize a UUID into the JSON-safe Celery task payload."""
        self._enqueue_task(str(document_id))


def get_ingestion_dispatcher() -> IngestionDispatcher:
    """Provide the production dispatcher as an overridable FastAPI dependency."""
    return CeleryIngestionDispatcher()
