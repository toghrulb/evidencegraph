"""Deterministic section-heading heuristic tests."""

from app.parsing.schemas import ParsedTextBlock
from app.parsing.sections import detect_heading, is_numbered_heading


def _block(text: str, *, bold: bool = False, size: float = 10, gap: float = 0) -> ParsedTextBlock:
    return ParsedTextBlock(
        block_index=0,
        page_number=1,
        raw_text=text,
        normalized_text=text,
        bbox=(0, 0, 100, 20),
        font_size=size,
        bold=bold,
        line_count=1,
        gap_before=gap,
    )


def test_common_and_numbered_headings_are_detected() -> None:
    assert detect_heading(_block("Methods"), estimated_body_size=10)
    assert is_numbered_heading("2. Methods")
    assert detect_heading(_block("2. Methods", bold=True), estimated_body_size=10)


def test_body_text_does_not_create_an_invented_heading() -> None:
    body = _block("The proposed method improves the measured result.")
    assert not detect_heading(body, estimated_body_size=10)
    assert not is_numbered_heading(body.normalized_text)
