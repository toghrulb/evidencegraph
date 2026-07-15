"""End-to-end integration coverage for Phase 1 infrastructure boundaries."""

from __future__ import annotations

import os
import time
from uuid import uuid4

import httpx
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 with the Compose stack running",
    ),
]

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def test_collection_upload_minio_duplicate_and_worker_status() -> None:
    """Exercise PostgreSQL, MinIO, Redis, Celery, and the API together."""
    base_url = os.getenv("INTEGRATION_API_URL", "http://localhost:8000")
    collection_id: str | None = None

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
                files={"file": ("integration.pdf", PDF_BYTES, "application/pdf")},
                data={"title": "Integration paper", "authors": "Test Author"},
            )
            assert uploaded.status_code == 201, uploaded.text
            document_id = uploaded.json()["id"]

            deadline = time.monotonic() + 15
            observed_status = uploaded.json()["status"]
            while observed_status == "uploaded" and time.monotonic() < deadline:
                time.sleep(0.2)
                status_response = client.get(f"/api/v1/documents/{document_id}/status")
                assert status_response.status_code == 200, status_response.text
                observed_status = status_response.json()["status"]
            assert observed_status == "processing"

            downloaded = client.get(f"/api/v1/documents/{document_id}/file")
            assert downloaded.status_code == 200, downloaded.text
            assert downloaded.content == PDF_BYTES

            duplicate = client.post(
                f"/api/v1/collections/{collection_id}/documents",
                files={"file": ("renamed.pdf", PDF_BYTES, "application/pdf")},
            )
            assert duplicate.status_code == 409, duplicate.text

            listed = client.get(f"/api/v1/collections/{collection_id}/documents")
            assert listed.status_code == 200, listed.text
            assert [item["id"] for item in listed.json()] == [document_id]
        finally:
            if collection_id is not None:
                deleted = client.delete(f"/api/v1/collections/{collection_id}")
                assert deleted.status_code in {204, 404}, deleted.text
