"""Database-backed Phase 2 processing and diagnostic API tests."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.chunking.types import ChunkingStrategy
from app.core.config import Settings
from app.ingestion.orchestrator import ProcessingOutcome, process_document
from app.models.chunk import Chunk
from app.models.collection import Collection
from app.models.document import Document, DocumentStatus
from tests.conftest import FakeStorage
from tests.pdf_factory import make_pdf


def _settings(*, strategy: ChunkingStrategy = ChunkingStrategy.SECTION_AWARE) -> Settings:
    return Settings(
        default_chunking_strategy=strategy,
        fixed_chunk_size=12,
        fixed_chunk_overlap=2,
        minimum_chunk_size=2,
        max_upload_mb=1,
        max_pdf_pages=20,
        parser_version="test-parser-v1",
        chunking_config_version="test-chunks-v1",
    )


def _stored_document(
    engine: Engine,
    storage: FakeStorage,
    content: bytes,
    *,
    strategy: ChunkingStrategy = ChunkingStrategy.SECTION_AWARE,
) -> UUID:
    collection_id = uuid4()
    document_id = uuid4()
    key = f"collections/{collection_id}/documents/{document_id}.pdf"
    storage.objects[key] = content
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        session.add(Collection(id=collection_id, name="Processing tests"))
        session.add(
            Document(
                id=document_id,
                collection_id=collection_id,
                title="Generated fixture",
                source_filename="fixture.pdf",
                storage_key=key,
                checksum=sha256(content).hexdigest(),
                status=DocumentStatus.UPLOADED,
                chunking_strategy=strategy,
            )
        )
        session.commit()
    return document_id


def _fixture_pdf() -> bytes:
    return make_pdf(
        [
            [
                ("1. Introduction", 16, True),
                ("Evidence graphs preserve source context and make claims inspectable.", 10, False),
            ],
            [
                ("2. Methods", 16, True),
                ("The deterministic parser processes each page in source order.", 10, False),
            ],
        ]
    )


def test_stored_pdf_reaches_ready_and_reprocessing_is_idempotent(
    sqlite_engine: Engine,
    fake_storage: FakeStorage,
) -> None:
    document_id = _stored_document(sqlite_engine, fake_storage, _fixture_pdf())
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)

    first_outcome = process_document(factory, fake_storage, _settings(), document_id)
    with factory() as session:
        document = session.get_one(Document, document_id)
        first_chunks = list(
            session.scalars(
                select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
            )
        )
        first_ids = {chunk.id for chunk in first_chunks}
        assert document.status == DocumentStatus.READY
        assert document.processing_stage == "ready"
        assert document.page_count == 2
        assert document.chunk_count == len(first_chunks) > 0
        assert document.chunking_strategy == ChunkingStrategy.SECTION_AWARE
        assert document.parsed_storage_key in fake_storage.objects
        assert [chunk.chunk_index for chunk in first_chunks] == list(range(len(first_chunks)))
        assert all(chunk.page_number <= chunk.end_page_number for chunk in first_chunks)

    second_outcome = process_document(factory, fake_storage, _settings(), document_id, force=True)
    with factory() as session:
        second_chunks = list(
            session.scalars(
                select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
            )
        )
        assert len(second_chunks) == len(first_chunks)
        assert {chunk.id for chunk in second_chunks}.isdisjoint(first_ids)
        assert [chunk.content for chunk in second_chunks] == [
            chunk.content for chunk in first_chunks
        ]

    assert first_outcome == ProcessingOutcome.READY
    assert second_outcome == ProcessingOutcome.READY


def test_failed_parse_sets_controlled_error_state(
    sqlite_engine: Engine,
    fake_storage: FakeStorage,
) -> None:
    document_id = _stored_document(sqlite_engine, fake_storage, b"%PDF-1.7\ninvalid")
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)

    outcome = process_document(factory, fake_storage, _settings(), document_id)

    with factory() as session:
        document = session.get_one(Document, document_id)
        assert outcome == ProcessingOutcome.FAILED
        assert document.status == DocumentStatus.FAILED
        assert document.processing_stage == "failed"
        assert document.error_code == "corrupt_pdf"
        assert document.error_message == "The PDF is corrupted or unreadable."
        assert document.processing_completed_at is not None
        assert session.scalar(select(func.count()).select_from(Chunk)) == 0


def test_textless_pdf_reports_ocr_as_unsupported(
    sqlite_engine: Engine,
    fake_storage: FakeStorage,
) -> None:
    document_id = _stored_document(sqlite_engine, fake_storage, make_pdf([[]]))
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)

    assert (
        process_document(factory, fake_storage, _settings(), document_id)
        == ProcessingOutcome.FAILED
    )
    with factory() as session:
        document = session.get_one(Document, document_id)
        assert document.error_code == "no_extractable_text"
        assert "OCR" in (document.error_message or "")


def test_failed_replacement_transaction_keeps_previous_valid_chunks(
    sqlite_engine: Engine,
    fake_storage: FakeStorage,
) -> None:
    document_id = _stored_document(sqlite_engine, fake_storage, _fixture_pdf())
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)
    assert (
        process_document(factory, fake_storage, _settings(), document_id) == ProcessingOutcome.READY
    )
    with factory() as session:
        before = [
            (chunk.id, chunk.content)
            for chunk in session.scalars(
                select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
            )
        ]

    def fail_insert(mapper: object, connection: object, target: Chunk) -> None:
        del mapper, connection, target
        raise SQLAlchemyError("simulated insert failure")

    event.listen(Chunk, "before_insert", fail_insert)
    try:
        outcome = process_document(factory, fake_storage, _settings(), document_id, force=True)
    finally:
        event.remove(Chunk, "before_insert", fail_insert)

    with factory() as session:
        after = [
            (chunk.id, chunk.content)
            for chunk in session.scalars(
                select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
            )
        ]
        document = session.get_one(Document, document_id)
        assert outcome == ProcessingOutcome.FAILED
        assert after == before
        assert document.error_code == "chunk_persistence_error"
        assert document.chunk_count == len(before)


def test_chunk_endpoint_is_paginated_and_document_delete_cascades(
    client: TestClient,
    sqlite_engine: Engine,
    fake_storage: FakeStorage,
) -> None:
    collection = client.post("/api/v1/collections", json={"name": "API chunks"}).json()
    content = _fixture_pdf()
    uploaded = client.post(
        f"/api/v1/collections/{collection['id']}/documents",
        files={"file": ("fixture.pdf", content, "application/pdf")},
        data={"chunking_strategy": "fixed_token"},
    )
    assert uploaded.status_code == 201
    document_id = UUID(uploaded.json()["id"])
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)
    assert (
        process_document(
            factory,
            fake_storage,
            _settings(strategy=ChunkingStrategy.FIXED_TOKEN),
            document_id,
        )
        == ProcessingOutcome.READY
    )

    first_page = client.get(f"/api/v1/documents/{document_id}/chunks?offset=0&limit=1")
    assert first_page.status_code == 200
    payload = first_page.json()
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1
    assert payload["total"] >= 1
    assert payload["items"][0]["chunking_strategy"] == "fixed_token"
    assert "storage_key" not in payload["items"][0]

    deleted = client.delete(f"/api/v1/documents/{document_id}")
    assert deleted.status_code == 204
    with factory() as session:
        assert (
            session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
            )
            == 0
        )
    assert client.get(f"/api/v1/documents/{document_id}/chunks").status_code == 404
