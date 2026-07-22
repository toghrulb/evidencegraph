"""Construction of the process-wide S3-compatible storage adapter."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings
from app.storage.base import ObjectStorage
from app.storage.s3 import S3ObjectStorage, S3StorageConfig


@lru_cache
def build_object_storage(
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
) -> ObjectStorage:
    """Build and cache storage from primitive, hashable settings values."""
    return S3ObjectStorage(
        S3StorageConfig(
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            bucket_name=bucket_name,
        )
    )


def storage_from_settings(settings: Settings) -> ObjectStorage:
    """Return the cached storage adapter for validated application settings."""
    return build_object_storage(
        settings.s3_endpoint_url,
        settings.s3_access_key,
        settings.s3_secret_key,
        settings.s3_bucket,
    )
