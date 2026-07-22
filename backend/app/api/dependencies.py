"""FastAPI dependencies for database and external-service adapters."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.ingestion.dispatcher import IngestionDispatcher, get_ingestion_dispatcher
from app.storage.base import ObjectStorage
from app.storage.factory import storage_from_settings


def get_object_storage(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ObjectStorage:
    """Return the process-wide MinIO/S3 adapter."""
    return storage_from_settings(settings)


DatabaseSession = Annotated[Session, Depends(get_db_session)]
StorageDependency = Annotated[ObjectStorage, Depends(get_object_storage)]
IngestionDependency = Annotated[IngestionDispatcher, Depends(get_ingestion_dispatcher)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
