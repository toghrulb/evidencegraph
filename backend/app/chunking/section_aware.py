"""Section-aware token-bounded chunking."""

from __future__ import annotations

from app.chunking.config import ChunkingConfig
from app.chunking.schemas import ChunkDraft
from app.chunking.tokenizer import Tokenizer
from app.chunking.windowing import TextGroup, chunk_groups
from app.parsing.schemas import ParsedDocument, ParsedParagraph


def section_aware_chunks(
    parsed_document: ParsedDocument,
    *,
    config: ChunkingConfig,
    tokenizer: Tokenizer,
) -> list[ChunkDraft]:
    """Keep consecutive logical sections separate while splitting oversized ones."""
    groups: list[TextGroup] = []
    pending: list[ParsedParagraph] = []
    current_section: str | None = None
    initialized = False

    for page in parsed_document.pages:
        for paragraph in page.paragraphs:
            if not paragraph.text.strip():
                continue
            if initialized and paragraph.section_title != current_section:
                groups.append(TextGroup(paragraphs=tuple(pending), section_title=current_section))
                pending = []
            current_section = paragraph.section_title
            initialized = True
            pending.append(paragraph)

    if pending:
        groups.append(TextGroup(paragraphs=tuple(pending), section_title=current_section))
    return chunk_groups(parsed_document, groups, config=config, tokenizer=tokenizer)
