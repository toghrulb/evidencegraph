"""Internal chunk drafts produced before database persistence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.chunking.types import ChunkingStrategy


class ChunkDraft(BaseModel):
    """Deterministic page-aware chunk ready for transactional insertion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_number: int = Field(ge=1)
    end_page_number: int = Field(ge=1)
    section_title: str | None = None
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    token_count: int = Field(gt=0)
    character_count: int = Field(gt=0)
    content_type: str = "text"
    chunking_strategy: ChunkingStrategy
    chunking_config_version: str
    metadata_json: dict[str, object]
