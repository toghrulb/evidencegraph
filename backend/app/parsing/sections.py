"""Deterministic research-paper section-title heuristics."""

from __future__ import annotations

import re
from statistics import median

from app.parsing.schemas import ParsedTextBlock

_NUMBERED_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[IVXLC]+\.?)\s+[A-Z][^\n]{0,100}$")
_COMMON_HEADINGS = {
    "abstract",
    "acknowledgements",
    "acknowledgments",
    "appendix",
    "background",
    "conclusion",
    "conclusions",
    "discussion",
    "evaluation",
    "experiments",
    "introduction",
    "limitations",
    "materials and methods",
    "method",
    "methodology",
    "methods",
    "related work",
    "references",
    "results",
}


def body_font_size(blocks: list[ParsedTextBlock]) -> float:
    """Estimate body size from non-empty layout blocks."""
    sizes = [block.font_size for block in blocks if block.normalized_text and block.font_size > 0]
    return float(median(sizes)) if sizes else 0.0


def is_numbered_heading(text: str) -> bool:
    """Return whether text resembles a numbered research-paper heading."""
    return bool(_NUMBERED_HEADING.fullmatch(_single_line(text)))


def detect_heading(block: ParsedTextBlock, *, estimated_body_size: float) -> bool:
    """Classify a short standalone block using layout and text signals."""
    text = _single_line(block.normalized_text)
    if not text or len(text) > 120 or len(text.split()) > 16 or block.line_count > 2:
        return False

    canonical = text.rstrip(":").casefold()
    common = canonical in _COMMON_HEADINGS
    numbered = is_numbered_heading(text)
    larger = estimated_body_size > 0 and block.font_size >= estimated_body_size * 1.15
    spaced = estimated_body_size > 0 and block.gap_before >= estimated_body_size * 0.75
    title_like = text.isupper() or text.istitle()

    if common:
        return True
    if numbered and (title_like or block.bold or larger):
        return True

    layout_score = sum((block.bold, larger, spaced, title_like))
    return layout_score >= 2 and not text.endswith((".", "?", "!"))


def heading_title(text: str) -> str:
    """Return a stable single-line section label without inventing content."""
    return _single_line(text).rstrip(":").strip()


def _single_line(text: str) -> str:
    return " ".join(text.split())
