"""S3-compatible object storage used by the local MinIO deployment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import BinaryIO, Protocol, cast

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

from app.storage.base import ObjectBody, StoredObject

_MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}
_MISSING_BUCKET_CODES = {"404", "NoSuchBucket", "NotFound"}
_BUCKET_ALREADY_OWNED_CODES = {"BucketAlreadyOwnedByYou"}


class StorageError(RuntimeError):
    """Base exception for controlled object-storage failures."""


class ObjectNotFoundError(StorageError):
    """Raised when a requested object does not exist."""


class _S3Client(Protocol):
    def head_bucket(self, **kwargs: object) -> object: ...

    def create_bucket(self, **kwargs: object) -> object: ...

    def put_object(self, **kwargs: object) -> object: ...

    def get_object(self, **kwargs: object) -> dict[str, object]: ...

    def delete_object(self, **kwargs: object) -> object: ...


@dataclass(frozen=True, slots=True)
class S3StorageConfig:
    """Constructor-injected connection and reliability settings."""

    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region_name: str = "us-east-1"
    connect_timeout_seconds: float = 3.0
    read_timeout_seconds: float = 30.0
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if not self.endpoint_url:
            raise ValueError("endpoint_url is required")
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError("S3 access credentials are required")
        if not self.bucket_name:
            raise ValueError("bucket_name is required")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("S3 timeouts must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


class S3ObjectStorage:
    """Store original documents through the S3 API exposed by MinIO."""

    def __init__(self, config: S3StorageConfig, *, client: _S3Client | None = None) -> None:
        self._config = config
        self._client = client or cast(
            _S3Client,
            boto3.client(
                "s3",
                endpoint_url=config.endpoint_url,
                aws_access_key_id=config.access_key_id,
                aws_secret_access_key=config.secret_access_key,
                region_name=config.region_name,
                config=Config(
                    connect_timeout=config.connect_timeout_seconds,
                    read_timeout=config.read_timeout_seconds,
                    retries={
                        "total_max_attempts": config.max_attempts,
                        "mode": "standard",
                    },
                    s3={"addressing_style": "path"},
                    signature_version="s3v4",
                ),
            ),
        )

    def ensure_bucket(self) -> None:
        """Create the bucket only when S3 confirms that it is absent."""

        try:
            self._client.head_bucket(Bucket=self._config.bucket_name)
            return
        except ClientError as exc:
            if _client_error_code(exc) not in _MISSING_BUCKET_CODES:
                raise StorageError("Could not inspect the object-storage bucket.") from exc
        except BotoCoreError as exc:
            raise StorageError("Could not connect to object storage.") from exc

        create_options: dict[str, object] = {"Bucket": self._config.bucket_name}
        if self._config.region_name != "us-east-1":
            create_options["CreateBucketConfiguration"] = {
                "LocationConstraint": self._config.region_name
            }
        try:
            self._client.create_bucket(**create_options)
        except ClientError as exc:
            if _client_error_code(exc) in _BUCKET_ALREADY_OWNED_CODES:
                return
            raise StorageError("Could not create the object-storage bucket.") from exc
        except BotoCoreError as exc:
            raise StorageError("Could not create the object-storage bucket.") from exc

    def upload_pdf(
        self,
        object_key: str,
        content: BinaryIO,
        *,
        size_bytes: int,
        content_type: str,
    ) -> None:
        """Upload one rewindable object using a generated, validated key."""

        _validate_object_key(object_key)
        if size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
        if not content_type:
            raise ValueError("content_type is required")

        content.seek(0)
        try:
            self._client.put_object(
                Bucket=self._config.bucket_name,
                Key=object_key,
                Body=content,
                ContentLength=size_bytes,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Could not store the document object.") from exc

    def open(self, object_key: str) -> StoredObject:
        """Return a streaming body without buffering the document in memory."""

        _validate_object_key(object_key)
        try:
            response = self._client.get_object(
                Bucket=self._config.bucket_name,
                Key=object_key,
            )
        except ClientError as exc:
            if _client_error_code(exc) in _MISSING_OBJECT_CODES:
                raise ObjectNotFoundError("The document object does not exist.") from exc
            raise StorageError("Could not read the document object.") from exc
        except BotoCoreError as exc:
            raise StorageError("Could not connect to object storage.") from exc

        raw_body = response.get("Body")
        if raw_body is None:
            raise StorageError("Object storage returned a response without a body.")
        body = cast(ObjectBody, raw_body)
        raw_size = response.get("ContentLength", 0)
        size_bytes = int(raw_size) if isinstance(raw_size, (int, str)) else 0
        content_type = str(response.get("ContentType", "application/octet-stream"))
        raw_etag = response.get("ETag")
        etag = str(raw_etag).strip('"') if raw_etag is not None else None
        return StoredObject(
            body=body,
            size_bytes=size_bytes,
            content_type=content_type,
            etag=etag,
        )

    def upload_bytes(self, object_key: str, content: bytes, *, content_type: str) -> None:
        """Upload an internal versioned artifact without exposing its key."""
        _validate_object_key(object_key)
        if not content_type:
            raise ValueError("content_type is required")
        try:
            self._client.put_object(
                Bucket=self._config.bucket_name,
                Key=object_key,
                Body=content,
                ContentLength=len(content),
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Could not store the internal document artifact.") from exc

    def delete(self, object_key: str) -> None:
        """Delete an object idempotently."""

        _validate_object_key(object_key)
        try:
            self._client.delete_object(
                Bucket=self._config.bucket_name,
                Key=object_key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Could not delete the document object.") from exc


def _validate_object_key(object_key: str) -> None:
    if not object_key or object_key.startswith("/") or "\\" in object_key:
        raise ValueError("object_key must be a non-empty relative key")
    if ".." in PurePosixPath(object_key).parts:
        raise ValueError("object_key cannot contain parent traversal segments")


def _client_error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
