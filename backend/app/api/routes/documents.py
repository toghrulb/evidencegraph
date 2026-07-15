"""PDF upload, metadata, status, file, and deletion endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    DatabaseSession,
    IngestionDependency,
    SettingsDependency,
    StorageDependency,
)
from app.documents.validation import (
    InvalidPdfMediaTypeError,
    PdfTooLargeError,
    PdfValidationError,
    validate_pdf_upload,
)
from app.schemas.document import DocumentRead, DocumentStatusRead
from app.services.documents import (
    DocumentCollectionNotFoundError,
    DocumentNotFoundError,
    DuplicateDocumentError,
    create_document,
    delete_document,
    get_document,
    list_documents,
)
from app.storage.base import ObjectBody
from app.storage.s3 import StorageError

router = APIRouter(tags=["documents"])


@router.post(
    "/api/v1/collections/{collection_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_endpoint(
    collection_id: UUID,
    file: Annotated[UploadFile, File(description="Original PDF paper")],
    session: DatabaseSession,
    storage: StorageDependency,
    dispatcher: IngestionDependency,
    settings: SettingsDependency,
    title: Annotated[str | None, Form(max_length=500)] = None,
    authors: Annotated[list[str] | None, Form()] = None,
    publication_year: Annotated[
        int | None,
        Form(ge=1000, le=datetime.now(tz=UTC).year + 1),
    ] = None,
) -> DocumentRead:
    """Validate and store a PDF, then enqueue its ingestion status transition."""
    try:
        validated = await validate_pdf_upload(
            file,
            max_size_bytes=settings.max_upload_mb * 1024 * 1024,
        )
    except InvalidPdfMediaTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except PdfTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    except PdfValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    with validated:
        try:
            document = create_document(
                session,
                storage,
                dispatcher,
                collection_id=collection_id,
                upload=validated,
                title=title,
                authors=authors,
                publication_year=publication_year,
            )
        except DocumentCollectionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except DuplicateDocumentError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Object storage is unavailable; the document was not created.",
            ) from exc
    return DocumentRead.model_validate(document)


@router.get(
    "/api/v1/collections/{collection_id}/documents",
    response_model=list[DocumentRead],
)
def list_documents_endpoint(
    collection_id: UUID,
    session: DatabaseSession,
) -> list[DocumentRead]:
    """List document metadata for a collection."""
    try:
        documents = list_documents(session, collection_id)
    except DocumentCollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [DocumentRead.model_validate(document) for document in documents]


@router.get("/api/v1/documents/{document_id}", response_model=DocumentRead)
def get_document_endpoint(
    document_id: UUID,
    session: DatabaseSession,
) -> DocumentRead:
    """Fetch stored document metadata."""
    try:
        document = get_document(session, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DocumentRead.model_validate(document)


@router.get("/api/v1/documents/{document_id}/status", response_model=DocumentStatusRead)
def get_document_status_endpoint(
    document_id: UUID,
    session: DatabaseSession,
) -> DocumentStatusRead:
    """Return the current asynchronous ingestion status."""
    try:
        document = get_document(session, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DocumentStatusRead.model_validate(document)


@router.get("/api/v1/documents/{document_id}/file")
def get_document_file_endpoint(
    document_id: UUID,
    session: DatabaseSession,
    storage: StorageDependency,
) -> StreamingResponse:
    """Stream the original PDF from object storage."""
    try:
        document = get_document(session, document_id)
        stored = storage.open(document.storage_key)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The stored PDF is temporarily unavailable.",
        ) from exc

    encoded_filename = quote(document.source_filename, safe="")
    headers = {
        "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
        "Content-Length": str(stored.size_bytes),
    }
    return StreamingResponse(
        _stream_body(stored.body),
        media_type="application/pdf",
        headers=headers,
    )


@router.delete("/api/v1/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_endpoint(
    document_id: UUID,
    session: DatabaseSession,
    storage: StorageDependency,
) -> Response:
    """Delete document metadata and the original stored PDF."""
    try:
        delete_document(session, storage, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is unavailable; the document was not deleted.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _stream_body(body: ObjectBody) -> Iterator[bytes]:
    try:
        while chunk := body.read(64 * 1024):
            yield chunk
    finally:
        body.close()
