"""Fixed-token chunking with conservative page crossing."""

from __future__ import annotations

from app.chunking.config import ChunkingConfig
from app.chunking.schemas import ChunkDraft
from app.chunking.tokenizer import Tokenizer
from app.chunking.windowing import TextGroup, chunk_groups
from app.parsing.schemas import ParsedDocument, ParsedParagraph


def fixed_token_chunks(
    parsed_document: ParsedDocument,
    *,
    config: ChunkingConfig,
    tokenizer: Tokenizer,
) -> list[ChunkDraft]:
    """Chunk pages independently unless a page is below the configured minimum."""
    groups: list[TextGroup] = []
    pending: list[ParsedParagraph] = []
    pending_tokens = 0

    for page in parsed_document.pages:
        page_paragraphs = [paragraph for paragraph in page.paragraphs if paragraph.text.strip()]
        if not page_paragraphs:
            continue
        if pending and pending_tokens >= config.minimum_chunk_size:
            groups.append(TextGroup(paragraphs=tuple(pending), section_title=None))
            pending = []
            pending_tokens = 0
        pending.extend(page_paragraphs)
        pending_tokens += sum(tokenizer.count(paragraph.text) for paragraph in page_paragraphs)

    if pending:
        groups.append(TextGroup(paragraphs=tuple(pending), section_title=None))
    return chunk_groups(parsed_document, groups, config=config, tokenizer=tokenizer)
