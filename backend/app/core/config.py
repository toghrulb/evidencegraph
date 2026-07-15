"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://evidencegraph:evidencegraph_local_only@localhost:5432/evidencegraph"
    )
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "evidencegraph"
    s3_secret_key: str = "evidencegraph_local_only"
    s3_bucket: str = "evidencegraph-papers"
    max_upload_mb: int = Field(default=50, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings object for the current process."""
    return Settings()
