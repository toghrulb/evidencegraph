"""Retry-safe orchestration for parsing and chunking stored PDFs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.chunking.config import ChunkingConfig
from app.chunking.persistence import replace_document_chunks
from app.chunking.service import chunk_document
from app.chunking.tokenizer import get_tokenizer
from app.chunking.types import ChunkingStrategy
from app.core.config import Settings
from app.ingestion.types import ProcessingStage
from app.models.document import Document, DocumentStatus
from app.parsing.errors import (
    DocumentProcessingError,
    NoExtractableTextError,
    StaleProcessingAttemptError,
    UnexpectedProcessingError,
)
from app.parsing.intermediate import parsed_document_key, store_parsed_document
from app.parsing.loader import load_stored_pdf
from app.parsing.parser import parse_pdf
from app.storage.base import ObjectStorage

logger = logging.getLogger("evidencegraph.ingestion")
SessionFactory = Callable[[], Session]


class ProcessingOutcome(StrEnum):
    """Terminal result of one ingestion task delivery."""

    READY = "ready"
    FAILED = "failed"
    NOT_FOUND = "not_found"
    ALREADY_READY = "already_ready"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class ProcessingContext:
    """Immutable metadata captured while claiming one processing attempt."""

    document_id: UUID
    collection_id: UUID
    attempt_id: UUID
    storage_key: str
    source_filename: str
    strategy: ChunkingStrategy


def process_document(
    session_factory: SessionFactory,
    storage: ObjectStorage,
    settings: Settings,
    document_id: UUID,
    *,
    force: bool = False,
    job_id: str | None = None,
) -> ProcessingOutcome:
    """Parse and chunk one document while making retries safe and observable."""
    context, early_outcome = _begin_attempt(session_factory, document_id, force=force)
    if context is None:
        return early_outcome

    log_context = {
        "document_id": str(context.document_id),
        "attempt_id": str(context.attempt_id),
    }
    if job_id is not None:
        log_context["job_id"] = job_id
    logger.info("document_processing_started", extra=log_context)
    try:
        _set_stage(session_factory, context, ProcessingStage.PARSING)
        pdf_bytes = load_stored_pdf(
            storage,
            context.storage_key,
            max_size_bytes=settings.max_upload_mb * 1024 * 1024,
        )
        parsed = parse_pdf(
            pdf_bytes,
            document_id=context.document_id,
            source_filename=context.source_filename,
            parser_version=settings.parser_version,
            max_pages=settings.max_pdf_pages,
        )
        if parsed.paragraph_count == 0:
            raise NoExtractableTextError

        parsed_key = parsed_document_key(context.collection_id, context.document_id)
        store_parsed_document(storage, parsed_key, parsed)

        _set_stage(session_factory, context, ProcessingStage.CHUNKING)
        tokenizer = get_tokenizer(settings.tokenizer_name)
        config = ChunkingConfig.from_settings(settings, strategy=context.strategy)
        drafts = chunk_document(parsed, config=config, tokenizer=tokenizer)
        if not drafts:
            raise NoExtractableTextError

        with session_factory() as session:
            replace_document_chunks(
                session,
                document_id=context.document_id,
                attempt_id=context.attempt_id,
                page_count=parsed.page_count,
                strategy=context.strategy,
                parsed_storage_key=parsed_key,
                drafts=drafts,
            )
        logger.info(
            "document_processing_completed",
            extra={**log_context, "stage": ProcessingStage.READY.value},
        )
        return ProcessingOutcome.READY
    except StaleProcessingAttemptError:
        logger.info("document_processing_superseded", extra=log_context)
        return ProcessingOutcome.SUPERSEDED
    except DocumentProcessingError as exc:
        _mark_failed(session_factory, context, exc)
        logger.warning(
            "document_processing_failed",
            extra={**log_context, "error_code": exc.code},
        )
        return ProcessingOutcome.FAILED
    except Exception:
        error = UnexpectedProcessingError()
        _mark_failed(session_factory, context, error)
        logger.exception(
            "document_processing_failed_unexpectedly",
            extra={**log_context, "error_code": error.code},
        )
        raise


def _begin_attempt(
    session_factory: SessionFactory,
    document_id: UUID,
    *,
    force: bool,
) -> tuple[ProcessingContext | None, ProcessingOutcome]:
    with session_factory() as session:
        document = session.get(Document, document_id, with_for_update=True)
        if document is None:
            session.rollback()
            return None, ProcessingOutcome.NOT_FOUND
        if document.status == DocumentStatus.READY and not force:
            session.rollback()
            return None, ProcessingOutcome.ALREADY_READY

        attempt_id = uuid4()
        document.status = DocumentStatus.PROCESSING
        document.processing_stage = ProcessingStage.PROCESSING
        document.processing_started_at = datetime.now(tz=UTC)
        document.processing_completed_at = None
        document.processing_attempt_id = attempt_id
        document.error_message = None
        document.error_code = None
        context = ProcessingContext(
            document_id=document.id,
            collection_id=document.collection_id,
            attempt_id=attempt_id,
            storage_key=document.storage_key,
            source_filename=document.source_filename,
            strategy=document.chunking_strategy,
        )
        session.commit()
        return context, ProcessingOutcome.READY


def _set_stage(
    session_factory: SessionFactory,
    context: ProcessingContext,
    stage: ProcessingStage,
) -> None:
    with session_factory() as session:
        document = session.get(Document, context.document_id, with_for_update=True)
        if document is None or document.processing_attempt_id != context.attempt_id:
            session.rollback()
            raise StaleProcessingAttemptError
        document.processing_stage = stage
        session.commit()


def _mark_failed(
    session_factory: SessionFactory,
    context: ProcessingContext,
    error: DocumentProcessingError,
) -> None:
    with session_factory() as session:
        document = session.get(Document, context.document_id, with_for_update=True)
        if document is None or document.processing_attempt_id != context.attempt_id:
            session.rollback()
            return
        document.status = DocumentStatus.FAILED
        document.processing_stage = ProcessingStage.FAILED
        document.error_message = error.user_message
        document.error_code = error.code
        document.processing_completed_at = datetime.now(tz=UTC)
        session.commit()
