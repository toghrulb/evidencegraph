"""Environment-backed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.chunking.types import ChunkingStrategy


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
    max_pdf_pages: int = Field(default=500, gt=0)
    default_chunking_strategy: ChunkingStrategy = ChunkingStrategy.SECTION_AWARE
    fixed_chunk_size: int = Field(default=512, gt=0)
    fixed_chunk_overlap: int = Field(default=64, ge=0)
    minimum_chunk_size: int = Field(default=64, gt=0)
    tokenizer_name: Literal["unicode_lexical_v1"] = "unicode_lexical_v1"
    parser_version: str = Field(default="pymupdf-v1", min_length=1, max_length=64)
    chunking_config_version: str = Field(default="v1", min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_chunking_settings(self) -> "Settings":
        """Reject combinations that cannot produce bounded chunks."""
        if self.fixed_chunk_overlap >= self.fixed_chunk_size:
            raise ValueError("FIXED_CHUNK_OVERLAP must be smaller than FIXED_CHUNK_SIZE")
        if self.minimum_chunk_size > self.fixed_chunk_size:
            raise ValueError("MINIMUM_CHUNK_SIZE cannot exceed FIXED_CHUNK_SIZE")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings object for the current process."""
    return Settings()
