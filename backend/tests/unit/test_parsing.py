"""Unit coverage for stored-PDF validation and page-aware parsing."""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import pytest
from tests.pdf_factory import make_encrypted_pdf, make_pdf

from app.parsing.errors import (
    CorruptPdfError,
    EncryptedPdfError,
    InvalidStoredPdfSignatureError,
    PdfPageLimitError,
    StoredPdfMissingError,
    StoredPdfTooLargeError,
)
from app.parsing.loader import load_stored_pdf
from app.parsing.normalization import normalize_inline_whitespace, normalize_text
from app.parsing.parser import parse_pdf
from app.storage.base import StoredObject
from app.storage.s3 import ObjectNotFoundError


class _StoredBytes:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def open(self, object_key: str) -> StoredObject:
        del object_key
        return StoredObject(
            body=BytesIO(self.content),
            size_bytes=len(self.content),
            content_type="application/pdf",
        )


class _MissingObject:
    def open(self, object_key: str) -> StoredObject:
        del object_key
        raise ObjectNotFoundError("missing")


def test_stored_pdf_signature_is_revalidated() -> None:
    with pytest.raises(InvalidStoredPdfSignatureError):
        load_stored_pdf(_StoredBytes(b"not-a-pdf"), "generated/key.pdf", max_size_bytes=100)


def test_stored_pdf_must_exist_and_remain_within_the_size_limit() -> None:
    with pytest.raises(StoredPdfMissingError):
        load_stored_pdf(_MissingObject(), "generated/missing.pdf", max_size_bytes=100)
    with pytest.raises(StoredPdfTooLargeError):
        load_stored_pdf(
            _StoredBytes(b"%PDF-" + b"x" * 100), "generated/large.pdf", max_size_bytes=20
        )


def test_corrupted_pdf_is_rejected_with_controlled_error() -> None:
    with pytest.raises(CorruptPdfError):
        parse_pdf(
            b"%PDF-1.7\nthis is not a readable object graph",
            document_id=uuid4(),
            source_filename="broken.pdf",
            parser_version="test-v1",
            max_pages=10,
        )


def test_encrypted_pdf_is_rejected_with_controlled_error() -> None:
    with pytest.raises(EncryptedPdfError):
        parse_pdf(
            make_encrypted_pdf(),
            document_id=uuid4(),
            source_filename="encrypted.pdf",
            parser_version="test-v1",
            max_pages=10,
        )


def test_empty_page_is_preserved_with_a_warning() -> None:
    parsed = parse_pdf(
        make_pdf([[]]),
        document_id=uuid4(),
        source_filename="empty.pdf",
        parser_version="test-v1",
        max_pages=10,
    )

    assert parsed.page_count == 1
    assert parsed.pages[0].page_number == 1
    assert parsed.pages[0].paragraphs == ()
    assert parsed.pages[0].warnings == ("no_extractable_text",)


def test_page_limit_is_enforced_before_extraction() -> None:
    with pytest.raises(PdfPageLimitError):
        parse_pdf(
            make_pdf([[], []]),
            document_id=uuid4(),
            source_filename="too-many-pages.pdf",
            parser_version="test-v1",
            max_pages=1,
        )


def test_whitespace_normalization_repairs_safe_wraps_and_keeps_paragraphs() -> None:
    assert normalize_inline_whitespace("  repeated\t spaces ") == "repeated spaces"
    normalized = normalize_text("The algo-\nrithm is deterministic.\n\n- first item\n- second item")

    assert normalized.startswith("The algorithm is deterministic.")
    assert "\n\n" in normalized
    assert "- first item\n- second item" in normalized


def test_normalization_removes_database_unsafe_control_characters() -> None:
    normalized = normalize_text("algo\x00rithm\n\n\x01Equation text\x7f")

    assert normalized == "algorithm\n\nEquation text"
    assert all(character not in normalized for character in ("\x00", "\x01", "\x7f"))


def test_parser_preserves_one_based_pages_paragraphs_and_detected_section() -> None:
    document_id = uuid4()
    parsed = parse_pdf(
        make_pdf(
            [
                [
                    ("1. Introduction", 16, True),
                    ("This is the first paragraph of the paper.", 10, False),
                    ("A second paragraph remains separate.", 10, False),
                ],
                [("Continuation text on page two.", 10, False)],
            ]
        ),
        document_id=document_id,
        source_filename="original.pdf",
        parser_version="test-v1",
        max_pages=10,
    )

    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert all(page.document_id == document_id for page in parsed.pages)
    assert parsed.pages[0].paragraphs[0].is_heading
    assert parsed.pages[0].paragraphs[1].section_title == "1. Introduction"
    assert parsed.pages[1].paragraphs[0].section_title == "1. Introduction"
    assert len(parsed.pages[0].paragraphs) == 3
