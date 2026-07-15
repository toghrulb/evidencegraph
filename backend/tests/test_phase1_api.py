"""API-level tests for Phase 1 collections and original PDF storage."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import FakeDispatcher, FakeStorage

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _create_collection(client: TestClient, name: str = "Research") -> dict[str, object]:
    response = client.post(
        "/api/v1/collections",
        json={"name": name, "description": "  Relevant papers  "},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def _upload_pdf(
    client: TestClient,
    collection_id: object,
    *,
    content: bytes = PDF_BYTES,
    filename: str = "paper.pdf",
    media_type: str = "application/pdf",
) -> object:
    return client.post(
        f"/api/v1/collections/{collection_id}/documents",
        files={"file": (filename, content, media_type)},
        data={"title": "A useful paper", "authors": "Ada Lovelace", "publication_year": "2025"},
    )


def test_collection_crud_and_validation(client: TestClient) -> None:
    """Collections can be created, listed, fetched, and deleted."""
    created = _create_collection(client)
    collection_id = created["id"]
    assert created["name"] == "Research"
    assert created["description"] == "Relevant papers"

    listed = client.get("/api/v1/collections")
    assert listed.status_code == status.HTTP_200_OK
    assert [item["id"] for item in listed.json()] == [collection_id]

    fetched = client.get(f"/api/v1/collections/{collection_id}")
    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json() == created

    invalid = client.post("/api/v1/collections", json={"name": "   "})
    assert invalid.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    deleted = client.delete(f"/api/v1/collections/{collection_id}")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert client.get(f"/api/v1/collections/{collection_id}").status_code == 404


def test_missing_collection_returns_not_found(client: TestClient) -> None:
    missing_id = uuid4()
    assert client.get(f"/api/v1/collections/{missing_id}").status_code == 404
    assert client.delete(f"/api/v1/collections/{missing_id}").status_code == 404
    assert client.get(f"/api/v1/collections/{missing_id}/documents").status_code == 404


def test_pdf_upload_metadata_status_download_and_delete(
    client: TestClient,
    fake_storage: FakeStorage,
    fake_dispatcher: FakeDispatcher,
) -> None:
    """One upload persists inspectable metadata and its retrievable original file."""
    collection = _create_collection(client)

    response = _upload_pdf(client, collection["id"], filename="../unsafe?.pdf")

    assert response.status_code == status.HTTP_201_CREATED
    document = response.json()
    document_id = UUID(document["id"])
    assert document["collection_id"] == collection["id"]
    assert document["title"] == "A useful paper"
    assert document["authors"] == ["Ada Lovelace"]
    assert document["publication_year"] == 2025
    assert document["source_filename"] == "unsafe_.pdf"
    assert document["checksum"] == hashlib.sha256(PDF_BYTES).hexdigest()
    assert document["status"] == "uploaded"
    assert "storage_key" not in document
    assert fake_dispatcher.document_ids == [document_id]
    assert len(fake_storage.objects) == 1

    listed = client.get(f"/api/v1/collections/{collection['id']}/documents")
    assert listed.status_code == 200
    assert listed.json() == [document]
    assert client.get(f"/api/v1/documents/{document_id}").json() == document

    status_response = client.get(f"/api/v1/documents/{document_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "uploaded"

    downloaded = client.get(f"/api/v1/documents/{document_id}/file")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert downloaded.content == PDF_BYTES

    deleted = client.delete(f"/api/v1/documents/{document_id}")
    assert deleted.status_code == 204
    assert fake_storage.objects == {}
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404


def test_duplicate_is_scoped_to_collection(
    client: TestClient,
    fake_storage: FakeStorage,
    fake_dispatcher: FakeDispatcher,
) -> None:
    first_collection = _create_collection(client, "First")
    second_collection = _create_collection(client, "Second")

    assert _upload_pdf(client, first_collection["id"]).status_code == 201
    duplicate = _upload_pdf(client, first_collection["id"])
    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in duplicate.json()["detail"]

    other_collection = _upload_pdf(client, second_collection["id"])
    assert other_collection.status_code == status.HTTP_201_CREATED
    assert len(fake_storage.objects) == 2
    assert len(fake_dispatcher.document_ids) == 2


def test_pdf_mime_signature_and_size_are_enforced(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    collection = _create_collection(client)

    wrong_mime = _upload_pdf(client, collection["id"], media_type="text/plain")
    assert wrong_mime.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    wrong_signature = _upload_pdf(client, collection["id"], content=b"not a pdf")
    assert wrong_signature.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    oversized = _upload_pdf(client, collection["id"], content=b"%PDF-" + b"x" * (1024 * 1024))
    assert oversized.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert fake_storage.objects == {}


def test_dispatch_failure_is_visible_as_failed_status(
    client: TestClient,
    fake_dispatcher: FakeDispatcher,
) -> None:
    collection = _create_collection(client)
    fake_dispatcher.should_fail = True

    uploaded = _upload_pdf(client, collection["id"])

    assert uploaded.status_code == status.HTTP_201_CREATED
    assert uploaded.json()["status"] == "failed"
    assert uploaded.json()["error_message"] == "The ingestion job could not be queued."


def test_storage_failures_do_not_claim_success_or_delete_metadata(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    collection = _create_collection(client)
    fake_storage.fail_upload = True
    failed_upload = _upload_pdf(client, collection["id"])
    assert failed_upload.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert client.get(f"/api/v1/collections/{collection['id']}/documents").json() == []
    assert len(fake_storage.deleted_keys) == 1

    fake_storage.fail_upload = False
    uploaded = _upload_pdf(client, collection["id"])
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]

    fake_storage.fail_delete = True
    failed_delete = client.delete(f"/api/v1/documents/{document_id}")
    assert failed_delete.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 200
    assert len(fake_storage.objects) == 1


def test_deleting_collection_removes_all_stored_documents(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    collection = _create_collection(client)
    first = _upload_pdf(client, collection["id"], content=PDF_BYTES + b"one")
    second = _upload_pdf(client, collection["id"], content=PDF_BYTES + b"two")
    assert first.status_code == 201
    assert second.status_code == 201
    assert len(fake_storage.objects) == 2

    response = client.delete(f"/api/v1/collections/{collection['id']}")

    assert response.status_code == 204
    assert fake_storage.objects == {}
    assert client.get(f"/api/v1/documents/{first.json()['id']}").status_code == 404
