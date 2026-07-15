"""Collection CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import DatabaseSession, StorageDependency
from app.schemas.collection import CollectionCreate, CollectionRead
from app.services.collections import (
    CollectionNotFoundError,
    create_collection,
    delete_collection,
    get_collection,
    list_collections,
)
from app.storage.s3 import StorageError

router = APIRouter(prefix="/api/v1/collections", tags=["collections"])


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
def create_collection_endpoint(
    data: CollectionCreate,
    session: DatabaseSession,
) -> CollectionRead:
    """Create a research collection."""
    return CollectionRead.model_validate(create_collection(session, data))


@router.get("", response_model=list[CollectionRead])
def list_collections_endpoint(session: DatabaseSession) -> list[CollectionRead]:
    """List all research collections."""
    return [CollectionRead.model_validate(item) for item in list_collections(session)]


@router.get("/{collection_id}", response_model=CollectionRead)
def get_collection_endpoint(
    collection_id: UUID,
    session: DatabaseSession,
) -> CollectionRead:
    """Fetch one research collection."""
    try:
        collection = get_collection(session, collection_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CollectionRead.model_validate(collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_endpoint(
    collection_id: UUID,
    session: DatabaseSession,
    storage: StorageDependency,
) -> Response:
    """Delete a collection, its document metadata, and stored PDFs."""
    try:
        delete_collection(session, storage, collection_id)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is unavailable; the collection was not deleted.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
