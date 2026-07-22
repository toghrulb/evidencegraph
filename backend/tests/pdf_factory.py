"""Small, original PDF fixtures generated entirely inside the test suite."""

from __future__ import annotations

from collections.abc import Sequence

import pymupdf

TextSpec = tuple[str, float, bool]


def make_pdf(pages: Sequence[Sequence[TextSpec]]) -> bytes:
    """Generate a compact text PDF with independently positioned text blocks."""
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    try:
        for page_specs in pages:
            page = document.new_page(width=595, height=842)  # type: ignore[no-untyped-call]
            top = 72.0
            for text, font_size, bold in page_specs:
                height = max(38.0, font_size * (text.count("\n") + 2))
                page.insert_textbox(  # type: ignore[no-untyped-call]
                    pymupdf.Rect(72, top, 523, top + height),
                    text,
                    fontsize=font_size,
                    fontname="hebo" if bold else "helv",
                )
                top += height + 16.0
        return bytes(document.tobytes(garbage=4, deflate=True))
    finally:
        document.close()  # type: ignore[no-untyped-call]


def make_encrypted_pdf() -> bytes:
    """Generate a password-protected PDF without external fixtures."""
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    try:
        page = document.new_page()  # type: ignore[no-untyped-call]
        page.insert_text((72, 72), "Protected research text")  # type: ignore[no-untyped-call]
        return bytes(
            document.tobytes(
                encryption=pymupdf.PDF_ENCRYPT_AES_256,
                owner_pw="owner-secret",
                user_pw="reader-secret",
            )
        )
    finally:
        document.close()  # type: ignore[no-untyped-call]
