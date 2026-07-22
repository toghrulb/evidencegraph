"""End-to-end Phase 2 coverage across the real Compose services."""

from __future__ import annotations

import os
import time
from uuid import uuid4

import httpx
import pytest

from app.ingestion.tasks import start_document_ingestion
from tests.pdf_factory import make_pdf

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 with the Compose stack running",
    ),
]


def _wait_for_terminal_status(
    client: httpx.Client,
    document_id: str,
    *,
    timeout_seconds: float = 30,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    payload: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/documents/{document_id}/status")
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] in {"ready", "failed"}:
            return payload
        time.sleep(0.2)
    raise AssertionError(f"document did not finish processing: {payload}")


def test_collection_upload_minio_queue_chunks_retry_and_failure() -> None:
    """Exercise PostgreSQL, MinIO, Redis, Celery, parsing, and chunk persistence."""
    base_url = os.getenv("INTEGRATION_API_URL", "http://localhost:8000")
    collection_id: str | None = None
    pdf_bytes = make_pdf(
        [
            [
                ("1. Introduction", 16, True),
                ("This generated fixture verifies page-aware asynchronous parsing.", 10, False),
            ],
            [
                ("2. Methods", 16, True),
                ("Chunks retain page ranges and deterministic source order.", 10, False),
            ],
        ]
    )

    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        try:
            created = client.post(
                "/api/v1/collections",
                json={"name": f"integration-{uuid4()}", "description": "temporary test data"},
            )
            assert created.status_code == 201, created.text
            collection_id = created.json()["id"]

            uploaded = client.post(
                f"/api/v1/collections/{collection_id}/documents",
                files={"file": ("integration.pdf", pdf_bytes, "application/pdf")},
                data={
                    "title": "Integration paper",
                    "authors": "Test Author",
                    "chunking_strategy": "section_aware",
                },
            )
            assert uploaded.status_code == 201, uploaded.text
            document_id = uploaded.json()["id"]

            terminal = _wait_for_terminal_status(client, document_id)
            assert terminal["status"] == "ready", terminal
            assert terminal["processing_stage"] == "ready"
            assert terminal["page_count"] == 2
            assert terminal["chunk_count"] > 0
            assert terminal["chunking_strategy"] == "section_aware"

            chunks = client.get(f"/api/v1/documents/{document_id}/chunks?limit=1")
            assert chunks.status_code == 200, chunks.text
            chunk_payload = chunks.json()
            original_chunk_count = chunk_payload["total"]
            assert original_chunk_count == terminal["chunk_count"]
            assert chunk_payload["items"][0]["page_number"] == 1
            assert chunk_payload["items"][0]["chunk_index"] == 0

            start_document_ingestion.delay(document_id)
            time.sleep(1)
            redelivered = client.get(f"/api/v1/documents/{document_id}/chunks?limit=1")
            assert redelivered.status_code == 200, redelivered.text
            assert redelivered.json()["total"] == original_chunk_count

            downloaded = client.get(f"/api/v1/documents/{document_id}/file")
            assert downloaded.status_code == 200, downloaded.text
            assert downloaded.content == pdf_bytes

            duplicate = client.post(
                f"/api/v1/collections/{collection_id}/documents",
                files={"file": ("renamed.pdf", pdf_bytes, "application/pdf")},
            )
            assert duplicate.status_code == 409, duplicate.text

            corrupted = client.post(
                f"/api/v1/collections/{collection_id}/documents",
                files={"file": ("corrupt.pdf", b"%PDF-1.7\ninvalid", "application/pdf")},
            )
            assert corrupted.status_code == 201, corrupted.text
            failed = _wait_for_terminal_status(client, corrupted.json()["id"])
            assert failed["status"] == "failed"
            assert failed["processing_stage"] == "failed"
            assert failed["error_code"] == "corrupt_pdf"
        finally:
            if collection_id is not None:
                deleted = client.delete(f"/api/v1/collections/{collection_id}")
                assert deleted.status_code in {204, 404}, deleted.text
