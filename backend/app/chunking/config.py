"""Validated chunking configuration shared by both strategies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.chunking.tokenizer import DEFAULT_TOKENIZER_NAME
from app.chunking.types import ChunkingStrategy
from app.core.config import Settings


class ChunkingConfig(BaseModel):
    """Versioned token bounds stored with every generated chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: ChunkingStrategy
    chunk_size: int = Field(gt=0)
    chunk_overlap: int = Field(ge=0)
    minimum_chunk_size: int = Field(gt=0)
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME
    config_version: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_bounds(self) -> ChunkingConfig:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.minimum_chunk_size > self.chunk_size:
            raise ValueError("minimum_chunk_size cannot exceed chunk_size")
        return self

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        strategy: ChunkingStrategy,
    ) -> ChunkingConfig:
        """Build the active strategy configuration from validated settings."""
        return cls(
            strategy=strategy,
            chunk_size=settings.fixed_chunk_size,
            chunk_overlap=settings.fixed_chunk_overlap,
            minimum_chunk_size=settings.minimum_chunk_size,
            tokenizer_name=settings.tokenizer_name,
            config_version=settings.chunking_config_version,
        )
