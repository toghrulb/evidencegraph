"""Focused tests for the Celery ingestion handoff."""

from unittest.mock import Mock
from uuid import uuid4

from app.core.config import Settings
from app.ingestion import tasks
from app.ingestion.dispatcher import CeleryIngestionDispatcher


def test_dispatcher_serializes_document_id_for_celery() -> None:
    enqueue_task = Mock()
    dispatcher = CeleryIngestionDispatcher(enqueue_task)
    document_id = uuid4()

    dispatcher.enqueue(document_id)

    enqueue_task.assert_called_once_with(str(document_id))


def test_worker_task_delegates_to_injected_orchestration_boundaries(monkeypatch) -> None:
    document_id = uuid4()
    settings = Settings()
    storage = Mock()
    processor = Mock()
    session_factory = Mock()
    monkeypatch.setattr(tasks, "get_settings", lambda: settings)
    monkeypatch.setattr(tasks, "storage_from_settings", lambda value: storage)
    monkeypatch.setattr(tasks, "process_document", processor)
    monkeypatch.setattr(tasks, "SessionLocal", session_factory)

    tasks.start_document_ingestion.run(str(document_id))

    processor.assert_called_once_with(
        session_factory,
        storage,
        settings,
        document_id,
        job_id=None,
    )
