"""Unit coverage for local tokenization and both chunking strategies."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.chunking.config import ChunkingConfig
from app.chunking.service import chunk_document
from app.chunking.tokenizer import UnicodeLexicalTokenizer
from app.chunking.types import ChunkingStrategy
from app.parsing.schemas import ParsedDocument, ParsedPage, ParsedParagraph


def _parsed(paragraphs: list[tuple[int, str, str | None]]) -> ParsedDocument:
    document_id = uuid4()
    pages: list[ParsedPage] = []
    paragraph_index = 0
    for page_number in sorted({item[0] for item in paragraphs}):
        page_paragraphs: list[ParsedParagraph] = []
        for source_page, text, section in paragraphs:
            if source_page != page_number:
                continue
            page_paragraphs.append(
                ParsedParagraph(
                    paragraph_index=paragraph_index,
                    block_index=paragraph_index,
                    page_number=page_number,
                    raw_text=text,
                    text=text,
                    section_title=section,
                )
            )
            paragraph_index += 1
        pages.append(
            ParsedPage(
                document_id=document_id,
                page_number=page_number,
                width=595,
                height=842,
                source_filename="fixture.pdf",
                raw_text="\n\n".join(item.raw_text for item in page_paragraphs),
                normalized_text="\n\n".join(item.text for item in page_paragraphs),
                section_title=page_paragraphs[0].section_title,
                paragraphs=tuple(page_paragraphs),
            )
        )
    return ParsedDocument(
        parser_version="test-v1",
        document_id=document_id,
        source_filename="fixture.pdf",
        pages=tuple(pages),
    )


def _config(
    strategy: ChunkingStrategy,
    *,
    size: int = 5,
    overlap: int = 2,
    minimum: int = 1,
) -> ChunkingConfig:
    return ChunkingConfig(
        strategy=strategy,
        chunk_size=size,
        chunk_overlap=overlap,
        minimum_chunk_size=minimum,
        config_version="test-v1",
    )


def test_token_counting_is_local_and_deterministic() -> None:
    tokenizer = UnicodeLexicalTokenizer()
    text = "Evidence-aware retrieval: version 2."
    assert tokenizer.count(text) == 6
    assert tokenizer.token_spans(text) == tokenizer.token_spans(text)
    assert tokenizer.slice_tokens(text, 0, 2) == "Evidence-aware retrieval"


def test_invalid_chunk_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _config(ChunkingStrategy.FIXED_TOKEN, size=5, overlap=5)
    with pytest.raises(ValidationError):
        _config(ChunkingStrategy.FIXED_TOKEN, size=5, minimum=6)


def test_fixed_token_boundaries_overlap_and_determinism() -> None:
    parsed = _parsed([(1, "zero one two three four five six seven eight nine ten eleven", None)])
    tokenizer = UnicodeLexicalTokenizer()
    config = _config(ChunkingStrategy.FIXED_TOKEN)

    first = chunk_document(parsed, config=config, tokenizer=tokenizer)
    second = chunk_document(parsed, config=config, tokenizer=tokenizer)

    assert first == second
    assert all(0 < chunk.token_count <= 5 for chunk in first)
    assert first[0].content.split()[-2:] == first[1].content.split()[:2]
    assert [chunk.chunk_index for chunk in first] == list(range(len(first)))
    assert all(chunk.content.strip() for chunk in first)
    signatures = {(chunk.content, chunk.page_number, chunk.end_page_number) for chunk in first}
    assert len(signatures) == len(first)


def test_fixed_token_records_cross_page_range_only_for_short_page() -> None:
    parsed = _parsed([(1, "one two", None), (2, "three four", None)])
    chunks = chunk_document(
        parsed,
        config=_config(ChunkingStrategy.FIXED_TOKEN, size=6, overlap=0, minimum=4),
        tokenizer=UnicodeLexicalTokenizer(),
    )

    assert len(chunks) == 1
    assert (chunks[0].page_number, chunks[0].end_page_number) == (1, 2)
    assert chunks[0].metadata_json["page_numbers"] == [1, 2]


def test_section_aware_chunks_never_merge_unrelated_sections() -> None:
    parsed = _parsed(
        [
            (1, "Introduction overview text", "Introduction"),
            (1, "Methods procedure text", "Methods"),
        ]
    )
    chunks = chunk_document(
        parsed,
        config=_config(ChunkingStrategy.SECTION_AWARE, size=20, overlap=2),
        tokenizer=UnicodeLexicalTokenizer(),
    )

    assert [chunk.section_title for chunk in chunks] == ["Introduction", "Methods"]
    assert "Methods" not in chunks[0].content
    assert "Introduction" not in chunks[1].content


def test_oversized_section_is_split_with_overlap_and_missing_heading_fallback() -> None:
    parsed = _parsed([(1, "one two three four five six seven eight nine ten eleven twelve", None)])
    chunks = chunk_document(
        parsed,
        config=_config(ChunkingStrategy.SECTION_AWARE, size=5, overlap=1),
        tokenizer=UnicodeLexicalTokenizer(),
    )

    assert len(chunks) > 1
    assert all(chunk.section_title is None for chunk in chunks)
    assert all(0 < chunk.token_count <= 5 for chunk in chunks)
    assert chunks[0].content.split()[-1:] == chunks[1].content.split()[:1]
