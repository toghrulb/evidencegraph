"""Shared isolated dependencies for Phase 1 API tests."""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from typing import BinaryIO
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_object_storage
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.ingestion.dispatcher import get_ingestion_dispatcher
from app.main import create_app
from app.storage.base import StoredObject
from app.storage.s3 import StorageError


class FakeStorage:
    """In-memory original-file storage implementing the production contract."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.ensure_bucket_calls = 0
        self.deleted_keys: list[str] = []
        self.fail_upload = False
        self.fail_delete = False

    def ensure_bucket(self) -> None:
        self.ensure_bucket_calls += 1

    def upload_pdf(
        self,
        object_key: str,
        content: BinaryIO,
        *,
        size_bytes: int,
        content_type: str,
    ) -> None:
        del content_type
        if self.fail_upload:
            raise StorageError("upload unavailable")
        content.seek(0)
        value = content.read()
        assert len(value) == size_bytes
        self.objects[object_key] = value

    def open(self, object_key: str) -> StoredObject:
        value = self.objects[object_key]
        return StoredObject(
            body=BytesIO(value),
            size_bytes=len(value),
            content_type="application/pdf",
        )

    def delete(self, object_key: str) -> None:
        if self.fail_delete:
            raise StorageError("delete unavailable")
        self.objects.pop(object_key, None)
        self.deleted_keys.append(object_key)


class FakeDispatcher:
    """Record queued identifiers without contacting Redis."""

    def __init__(self) -> None:
        self.document_ids: list[UUID] = []
        self.should_fail = False

    def enqueue(self, document_id: UUID) -> None:
        if self.should_fail:
            raise RuntimeError("queue unavailable")
        self.document_ids.append(document_id)


@pytest.fixture
def sqlite_engine() -> Iterator[Engine]:
    """Create one foreign-key-aware in-memory database per test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def fake_dispatcher() -> FakeDispatcher:
    return FakeDispatcher()


@pytest.fixture
def application(
    sqlite_engine: Engine,
    fake_storage: FakeStorage,
    fake_dispatcher: FakeDispatcher,
) -> Iterator[FastAPI]:
    """Build an API instance with all external effects replaced by local fakes."""
    test_session = sessionmaker(bind=sqlite_engine, autoflush=False, expire_on_commit=False)

    def override_session() -> Iterator[Session]:
        with test_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_object_storage] = lambda: fake_storage
    app.dependency_overrides[get_ingestion_dispatcher] = lambda: fake_dispatcher
    app.dependency_overrides[get_settings] = lambda: Settings(max_upload_mb=1)
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client
