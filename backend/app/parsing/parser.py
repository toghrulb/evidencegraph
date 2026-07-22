"""Layout-aware page-by-page extraction using PyMuPDF."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

import pymupdf

from app.parsing.errors import CorruptPdfError, EncryptedPdfError, PdfPageLimitError
from app.parsing.normalization import normalize_paragraph
from app.parsing.schemas import ParsedDocument, ParsedPage, ParsedParagraph, ParsedTextBlock
from app.parsing.sections import body_font_size, detect_heading, heading_title

_BOLD_FLAG = 1 << 4


def parse_pdf(
    pdf_bytes: bytes,
    *,
    document_id: UUID,
    source_filename: str,
    parser_version: str,
    max_pages: int,
) -> ParsedDocument:
    """Extract ordered layout blocks, paragraphs, and section labels page by page."""
    try:
        document = pymupdf.open(  # type: ignore[no-untyped-call]
            stream=pdf_bytes,
            filetype="pdf",
        )
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise CorruptPdfError from exc

    try:
        if document.needs_pass or document.is_encrypted:
            raise EncryptedPdfError
        encryption = document.metadata.get("encryption") if document.metadata else None
        if encryption:
            raise EncryptedPdfError
        if document.is_repaired:
            raise CorruptPdfError("PyMuPDF had to repair the PDF structure.")
        if document.page_count < 1:
            raise CorruptPdfError("The PDF does not contain any pages.")
        if document.page_count > max_pages:
            raise PdfPageLimitError

        extracted = [
            _extract_page(
                document.load_page(page_index),  # type: ignore[no-untyped-call]
                page_number=page_index + 1,
            )
            for page_index in range(document.page_count)
        ]
    except (EncryptedPdfError, CorruptPdfError, PdfPageLimitError):
        raise
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise CorruptPdfError from exc
    finally:
        document.close()  # type: ignore[no-untyped-call]

    flat_blocks = [block for page in extracted for block in page.blocks]
    estimated_body_size = body_font_size(flat_blocks)
    heading_keys = {
        (block.page_number, block.block_index)
        for block in flat_blocks
        if detect_heading(block, estimated_body_size=estimated_body_size)
    }

    current_section: str | None = None
    paragraph_index = 0
    parsed_pages: list[ParsedPage] = []
    for extracted_page in extracted:
        page_blocks: list[ParsedTextBlock] = []
        paragraphs: list[ParsedParagraph] = []
        page_section = current_section
        for block in extracted_page.blocks:
            is_heading = (block.page_number, block.block_index) in heading_keys
            updated_block = block.model_copy(update={"is_heading": is_heading})
            page_blocks.append(updated_block)
            if is_heading:
                current_section = heading_title(block.normalized_text)
                if page_section is None:
                    page_section = current_section
            paragraphs.append(
                ParsedParagraph(
                    paragraph_index=paragraph_index,
                    block_index=block.block_index,
                    page_number=block.page_number,
                    raw_text=block.raw_text,
                    text=block.normalized_text,
                    section_title=current_section,
                    is_heading=is_heading,
                )
            )
            paragraph_index += 1

        parsed_pages.append(
            ParsedPage(
                document_id=document_id,
                page_number=extracted_page.page_number,
                width=extracted_page.width,
                height=extracted_page.height,
                source_filename=source_filename,
                raw_text="\n\n".join(block.raw_text for block in page_blocks),
                normalized_text="\n\n".join(block.normalized_text for block in page_blocks),
                section_title=page_section,
                blocks=tuple(page_blocks),
                paragraphs=tuple(paragraphs),
                warnings=tuple(extracted_page.warnings),
            )
        )

    warnings = tuple(
        f"page_{page.page_number}:{warning}" for page in parsed_pages for warning in page.warnings
    )
    return ParsedDocument(
        parser_version=parser_version,
        document_id=document_id,
        source_filename=source_filename,
        pages=tuple(parsed_pages),
        warnings=warnings,
    )


class _ExtractedPage:
    def __init__(
        self,
        *,
        page_number: int,
        width: float,
        height: float,
        blocks: list[ParsedTextBlock],
        warnings: list[str],
    ) -> None:
        self.page_number = page_number
        self.width = width
        self.height = height
        self.blocks = blocks
        self.warnings = warnings


def _extract_page(page: pymupdf.Page, *, page_number: int) -> _ExtractedPage:
    layout = cast(
        Mapping[str, Any],
        page.get_text("dict", sort=True),  # type: ignore[no-untyped-call]
    )
    raw_blocks = cast(list[Mapping[str, Any]], layout.get("blocks", []))
    blocks: list[ParsedTextBlock] = []
    warnings: list[str] = []
    previous_bottom = 0.0
    ignored_images = False

    for source_index, raw_block in enumerate(raw_blocks):
        if int(raw_block.get("type", -1)) != 0:
            ignored_images = True
            continue

        raw_lines = cast(list[Mapping[str, Any]], raw_block.get("lines", []))
        line_texts: list[str] = []
        span_sizes: list[float] = []
        bold = False
        for raw_line in raw_lines:
            raw_spans = cast(list[Mapping[str, Any]], raw_line.get("spans", []))
            line_texts.append("".join(str(span.get("text", "")) for span in raw_spans))
            for span in raw_spans:
                span_sizes.append(float(span.get("size", 0.0)))
                font_name = str(span.get("font", "")).casefold()
                flags = int(span.get("flags", 0))
                bold = bold or bool(flags & _BOLD_FLAG) or "bold" in font_name

        raw_text = "\n".join(line_texts).strip()
        normalized_text = normalize_paragraph(raw_text)
        if not normalized_text:
            continue

        bbox_values = tuple(float(value) for value in cast(tuple[float, ...], raw_block["bbox"]))
        if len(bbox_values) != 4:
            continue
        bbox = (bbox_values[0], bbox_values[1], bbox_values[2], bbox_values[3])
        gap_before = max(0.0, bbox[1] - previous_bottom)
        previous_bottom = max(previous_bottom, bbox[3])
        blocks.append(
            ParsedTextBlock(
                block_index=source_index,
                page_number=page_number,
                raw_text=raw_text,
                normalized_text=normalized_text,
                bbox=bbox,
                font_size=max(span_sizes, default=0.0),
                bold=bold,
                line_count=max(1, len(raw_lines)),
                gap_before=gap_before,
            )
        )

    if ignored_images:
        warnings.append("image_blocks_ignored")
    if not blocks:
        warnings.append("no_extractable_text")
    elif any("\ufffd" in block.normalized_text for block in blocks):
        warnings.append("replacement_characters_present")

    return _ExtractedPage(
        page_number=page_number,
        width=float(page.rect.width),
        height=float(page.rect.height),
        blocks=blocks,
        warnings=warnings,
    )
