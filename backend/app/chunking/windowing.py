"""Shared token-window assembly with paragraph-aware boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from app.chunking.config import ChunkingConfig
from app.chunking.schemas import ChunkDraft
from app.chunking.tokenizer import Tokenizer
from app.parsing.schemas import ParsedDocument, ParsedParagraph


@dataclass(frozen=True, slots=True)
class TextGroup:
    """Paragraphs that a strategy permits to share chunks."""

    paragraphs: tuple[ParsedParagraph, ...]
    section_title: str | None


@dataclass(frozen=True, slots=True)
class _ParagraphSpan:
    paragraph: ParsedParagraph
    start_token: int
    end_token: int


def chunk_groups(
    parsed_document: ParsedDocument,
    groups: list[TextGroup],
    *,
    config: ChunkingConfig,
    tokenizer: Tokenizer,
) -> list[ChunkDraft]:
    """Turn strategy-defined groups into deterministic overlapping windows."""
    drafts: list[ChunkDraft] = []
    signatures: set[tuple[str, int, int, tuple[int, ...]]] = set()
    for group in groups:
        for draft in _chunk_group(
            parsed_document,
            group,
            config=config,
            tokenizer=tokenizer,
        ):
            raw_paragraph_indices = draft.metadata_json.get("paragraph_indices", [])
            paragraph_indices = (
                tuple(int(value) for value in raw_paragraph_indices)
                if isinstance(raw_paragraph_indices, list)
                else ()
            )
            signature = (
                draft.content,
                draft.page_number,
                draft.end_page_number,
                paragraph_indices,
            )
            if signature in signatures:
                continue
            signatures.add(signature)
            drafts.append(draft.model_copy(update={"chunk_index": len(drafts)}))
    return drafts


def _chunk_group(
    parsed_document: ParsedDocument,
    group: TextGroup,
    *,
    config: ChunkingConfig,
    tokenizer: Tokenizer,
) -> list[ChunkDraft]:
    paragraphs = tuple(paragraph for paragraph in group.paragraphs if paragraph.text.strip())
    if not paragraphs:
        return []

    content, paragraph_spans = _join_paragraphs(paragraphs, tokenizer)
    tokens = tokenizer.token_spans(content)
    total_tokens = len(tokens)
    if total_tokens == 0:
        return []

    drafts: list[ChunkDraft] = []
    start = 0
    while start < total_tokens:
        maximum_end = min(start + config.chunk_size, total_tokens)
        end = _preferred_end(
            start,
            maximum_end,
            total_tokens,
            paragraph_spans,
            config=config,
        )
        if end <= start:
            raise RuntimeError("chunk window did not advance")

        chunk_content = content[tokens[start].start : tokens[end - 1].end].strip()
        intersecting = tuple(
            span for span in paragraph_spans if span.end_token > start and span.start_token < end
        )
        if chunk_content and intersecting:
            page_numbers = sorted({span.paragraph.page_number for span in intersecting})
            section_titles = list(
                dict.fromkeys(
                    span.paragraph.section_title
                    for span in intersecting
                    if span.paragraph.section_title is not None
                )
            )
            token_count = tokenizer.count(chunk_content)
            drafts.append(
                ChunkDraft(
                    page_number=page_numbers[0],
                    end_page_number=page_numbers[-1],
                    section_title=group.section_title
                    or (section_titles[0] if section_titles else None),
                    chunk_index=len(drafts),
                    content=chunk_content,
                    token_count=token_count,
                    character_count=len(chunk_content),
                    content_type=(
                        "heading"
                        if all(span.paragraph.is_heading for span in intersecting)
                        else "text"
                    ),
                    chunking_strategy=config.strategy,
                    chunking_config_version=config.config_version,
                    metadata_json={
                        "schema_version": parsed_document.schema_version,
                        "parser_version": parsed_document.parser_version,
                        "tokenizer_name": tokenizer.name,
                        "source_filename": parsed_document.source_filename,
                        "paragraph_indices": [
                            span.paragraph.paragraph_index for span in intersecting
                        ],
                        "page_numbers": page_numbers,
                        "section_titles": section_titles,
                        "chunk_size": config.chunk_size,
                        "chunk_overlap": config.chunk_overlap,
                        "minimum_chunk_size": config.minimum_chunk_size,
                        "below_minimum": token_count < config.minimum_chunk_size,
                    },
                )
            )

        if end == total_tokens:
            break
        start = _next_start(
            start,
            end,
            paragraph_spans,
            overlap=config.chunk_overlap,
        )
    return drafts


def _join_paragraphs(
    paragraphs: tuple[ParsedParagraph, ...],
    tokenizer: Tokenizer,
) -> tuple[str, tuple[_ParagraphSpan, ...]]:
    content = "\n\n".join(paragraph.text.strip() for paragraph in paragraphs)
    spans: list[_ParagraphSpan] = []
    token_cursor = 0
    for paragraph in paragraphs:
        token_count = tokenizer.count(paragraph.text.strip())
        spans.append(
            _ParagraphSpan(
                paragraph=paragraph,
                start_token=token_cursor,
                end_token=token_cursor + token_count,
            )
        )
        token_cursor += token_count
    return content, tuple(spans)


def _preferred_end(
    start: int,
    maximum_end: int,
    total_tokens: int,
    paragraph_spans: tuple[_ParagraphSpan, ...],
    *,
    config: ChunkingConfig,
) -> int:
    if maximum_end == total_tokens:
        return total_tokens

    minimum_end = min(start + config.minimum_chunk_size, maximum_end)
    candidates = [
        span.end_token for span in paragraph_spans if minimum_end <= span.end_token <= maximum_end
    ]
    for candidate in sorted(candidates, reverse=True):
        next_start = max(start + 1, candidate - config.chunk_overlap)
        if total_tokens - next_start >= config.minimum_chunk_size:
            return candidate

    adjusted_end = total_tokens + config.chunk_overlap - config.minimum_chunk_size
    if minimum_end <= adjusted_end < maximum_end:
        return adjusted_end
    return maximum_end


def _next_start(
    previous_start: int,
    end: int,
    paragraph_spans: tuple[_ParagraphSpan, ...],
    *,
    overlap: int,
) -> int:
    desired = max(previous_start + 1, end - overlap)
    paragraph_starts = sorted(
        span.start_token for span in paragraph_spans if desired <= span.start_token < end
    )
    next_start = paragraph_starts[0] if paragraph_starts else desired
    return next_start if next_start > previous_start else end
