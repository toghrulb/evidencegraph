"""FastAPI dependencies for database and external-service adapters."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.ingestion.dispatcher import IngestionDispatcher, get_ingestion_dispatcher
from app.storage.base import ObjectStorage
from app.storage.s3 import S3ObjectStorage, S3StorageConfig


@lru_cache
def _build_object_storage(
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
) -> ObjectStorage:
    return S3ObjectStorage(
        S3StorageConfig(
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            bucket_name=bucket_name,
        )
    )


def get_object_storage(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ObjectStorage:
    """Return the process-wide MinIO/S3 adapter."""
    return _build_object_storage(
        settings.s3_endpoint_url,
        settings.s3_access_key,
        settings.s3_secret_key,
        settings.s3_bucket,
    )


DatabaseSession = Annotated[Session, Depends(get_db_session)]
StorageDependency = Annotated[ObjectStorage, Depends(get_object_storage)]
IngestionDependency = Annotated[IngestionDispatcher, Depends(get_ingestion_dispatcher)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
