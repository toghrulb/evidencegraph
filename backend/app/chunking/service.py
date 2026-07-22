"""Strategy selection for project-owned chunking implementations."""

from __future__ import annotations

from app.chunking.config import ChunkingConfig
from app.chunking.fixed import fixed_token_chunks
from app.chunking.schemas import ChunkDraft
from app.chunking.section_aware import section_aware_chunks
from app.chunking.tokenizer import Tokenizer
from app.chunking.types import ChunkingStrategy
from app.parsing.schemas import ParsedDocument


def chunk_document(
    parsed_document: ParsedDocument,
    *,
    config: ChunkingConfig,
    tokenizer: Tokenizer,
) -> list[ChunkDraft]:
    """Run the configured deterministic chunker."""
    if config.strategy == ChunkingStrategy.FIXED_TOKEN:
        return fixed_token_chunks(parsed_document, config=config, tokenizer=tokenizer)
    if config.strategy == ChunkingStrategy.SECTION_AWARE:
        return section_aware_chunks(parsed_document, config=config, tokenizer=tokenizer)
    raise ValueError(f"Unsupported chunking strategy: {config.strategy}")
