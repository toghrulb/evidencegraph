"""Collection persistence operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection import Collection
from app.models.document import Document
from app.schemas.collection import CollectionCreate
from app.storage.base import ObjectStorage


class CollectionNotFoundError(LookupError):
    """Raised when a collection identifier does not exist."""


def create_collection(session: Session, data: CollectionCreate) -> Collection:
    """Persist and return a collection."""
    collection = Collection(name=data.name, description=data.description)
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def list_collections(session: Session) -> list[Collection]:
    """Return collections in stable newest-first order."""
    statement = select(Collection).order_by(Collection.created_at.desc(), Collection.id)
    return list(session.scalars(statement))


def get_collection(session: Session, collection_id: UUID) -> Collection:
    """Return a collection or raise a controlled not-found error."""
    collection = session.get(Collection, collection_id)
    if collection is None:
        raise CollectionNotFoundError(f"Collection {collection_id} does not exist.")
    return collection


def delete_collection(
    session: Session,
    storage: ObjectStorage,
    collection_id: UUID,
) -> None:
    """Delete a collection and every original PDF stored for it."""
    collection = session.scalar(
        select(Collection).where(Collection.id == collection_id).with_for_update()
    )
    if collection is None:
        raise CollectionNotFoundError(f"Collection {collection_id} does not exist.")
    keys = session.scalars(
        select(Document.storage_key).where(Document.collection_id == collection_id)
    ).all()
    for key in keys:
        storage.delete(key)

    session.delete(collection)
    session.commit()
