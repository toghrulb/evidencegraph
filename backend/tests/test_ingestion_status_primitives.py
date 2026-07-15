"""Focused tests for the Phase 1 asynchronous ingestion handoff."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.ingestion.dispatcher import CeleryIngestionDispatcher
from app.ingestion.tasks import IngestionClaimResult, claim_document_for_ingestion
from app.models.document import Document, DocumentStatus


def test_dispatcher_serializes_document_id_for_celery() -> None:
    enqueue_task = Mock()
    dispatcher = CeleryIngestionDispatcher(enqueue_task)
    document_id = uuid4()

    dispatcher.enqueue(document_id)

    enqueue_task.assert_called_once_with(str(document_id))


def test_uploaded_document_is_claimed_once() -> None:
    document = SimpleNamespace(
        status=DocumentStatus.UPLOADED,
        error_message="stale error",
    )
    session = Mock(spec=Session)
    session.get.return_value = document
    document_id = uuid4()

    result = claim_document_for_ingestion(session, document_id)

    assert result == IngestionClaimResult.CLAIMED
    assert document.status == DocumentStatus.PROCESSING
    assert document.error_message is None
    session.get.assert_called_once_with(Document, document_id, with_for_update=True)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_redelivered_document_is_not_claimed_again() -> None:
    document = SimpleNamespace(
        status=DocumentStatus.PROCESSING,
        error_message=None,
    )
    session = Mock(spec=Session)
    session.get.return_value = document

    result = claim_document_for_ingestion(session, uuid4())

    assert result == IngestionClaimResult.NOT_UPLOADED
    assert document.status == DocumentStatus.PROCESSING
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


def test_missing_document_is_a_safe_no_op() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None

    result = claim_document_for_ingestion(session, uuid4())

    assert result == IngestionClaimResult.NOT_FOUND
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()
