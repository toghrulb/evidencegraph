"""Unit tests for controlled S3/MinIO adapter behavior."""

from __future__ import annotations

from io import BytesIO

from botocore.exceptions import ClientError

from app.storage.s3 import S3ObjectStorage, S3StorageConfig


def _client_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, operation)


class BucketCreationRaceClient:
    """Simulate another request creating the configured bucket first."""

    def __init__(self) -> None:
        self.create_calls = 0

    def head_bucket(self, **kwargs: object) -> object:
        del kwargs
        raise _client_error("404", "HeadBucket")

    def create_bucket(self, **kwargs: object) -> object:
        del kwargs
        self.create_calls += 1
        raise _client_error("BucketAlreadyOwnedByYou", "CreateBucket")

    def put_object(self, **kwargs: object) -> object:
        del kwargs
        return {}

    def get_object(self, **kwargs: object) -> dict[str, object]:
        del kwargs
        return {"Body": BytesIO(), "ContentLength": 0, "ContentType": "application/pdf"}

    def delete_object(self, **kwargs: object) -> object:
        del kwargs
        return {}


def test_bucket_creation_is_safe_when_another_upload_wins_the_race() -> None:
    client = BucketCreationRaceClient()
    storage = S3ObjectStorage(
        S3StorageConfig(
            endpoint_url="http://minio:9000",
            access_key_id="access",
            secret_access_key="secret",
            bucket_name="papers",
        ),
        client=client,
    )

    storage.ensure_bucket()

    assert client.create_calls == 1
