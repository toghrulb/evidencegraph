"""Versioned internal parsed-document schemas independent of HTTP responses."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PARSED_DOCUMENT_SCHEMA_VERSION = "1"


class InternalSchema(BaseModel):
    """Strict immutable base for deterministic intermediate data."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ParsedTextBlock(InternalSchema):
    """One layout-preserving PyMuPDF text block."""

    block_index: int = Field(ge=0)
    page_number: int = Field(ge=1)
    raw_text: str
    normalized_text: str
    bbox: tuple[float, float, float, float]
    font_size: float = Field(ge=0)
    bold: bool
    line_count: int = Field(ge=1)
    gap_before: float = Field(ge=0)
    is_heading: bool = False


class ParsedParagraph(InternalSchema):
    """Normalized paragraph with its source block and active section."""

    paragraph_index: int = Field(ge=0)
    block_index: int = Field(ge=0)
    page_number: int = Field(ge=1)
    raw_text: str
    text: str
    section_title: str | None = None
    is_heading: bool = False


class ParsedPage(InternalSchema):
    """One-based page extraction with layout and warning metadata."""

    document_id: UUID
    page_number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    source_filename: str
    raw_text: str
    normalized_text: str
    section_title: str | None = None
    blocks: tuple[ParsedTextBlock, ...] = ()
    paragraphs: tuple[ParsedParagraph, ...] = ()
    warnings: tuple[str, ...] = ()


class ParsedDocument(InternalSchema):
    """Serializable parser output stored as versioned JSON in object storage."""

    schema_version: str = PARSED_DOCUMENT_SCHEMA_VERSION
    parser_version: str
    document_id: UUID
    source_filename: str
    pages: tuple[ParsedPage, ...]
    warnings: tuple[str, ...] = ()

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def paragraph_count(self) -> int:
        return sum(len(page.paragraphs) for page in self.pages)
