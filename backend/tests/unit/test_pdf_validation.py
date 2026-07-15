from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from tempfile import SpooledTemporaryFile

import pytest

from app.documents.validation import (
    InvalidPdfFilenameError,
    InvalidPdfMediaTypeError,
    InvalidPdfSignatureError,
    PdfTooLargeError,
    sanitize_source_filename,
    validate_pdf_upload,
)


class UploadStub:
    def __init__(
        self,
        content: bytes,
        *,
        filename: str | None = "paper.pdf",
        content_type: str | None = "application/pdf",
    ) -> None:
        self.filename = filename
        self.content_type = content_type
        self._content = BytesIO(content)
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self._content.read(size)


def test_validate_pdf_streams_hashes_and_rewinds_upload() -> None:
    payload = b"%PDF-1.7\nsmall test document"
    upload = UploadStub(payload, filename=r"C:\fakepath\Research ? Notes.pdf")

    result = asyncio.run(
        validate_pdf_upload(
            upload,
            max_size_bytes=1024,
            spool_size_bytes=8,
            read_size_bytes=7,
        )
    )

    try:
        assert isinstance(result.file, SpooledTemporaryFile)
        assert result.source_filename == "Research _ Notes.pdf"
        assert result.size_bytes == len(payload)
        assert result.checksum == hashlib.sha256(payload).hexdigest()
        assert result.content_type == "application/pdf"
        assert result.file.tell() == 0
        assert result.file.read() == payload
        assert len(upload.read_sizes) > 2
        assert set(upload.read_sizes) == {7}
    finally:
        result.close()


@pytest.mark.parametrize("content_type", [None, "", "text/plain", "application/octet-stream"])
def test_validate_pdf_rejects_non_pdf_media_types(content_type: str | None) -> None:
    upload = UploadStub(b"%PDF-1.7\n", content_type=content_type)

    with pytest.raises(InvalidPdfMediaTypeError, match="application/pdf"):
        asyncio.run(validate_pdf_upload(upload, max_size_bytes=1024))


def test_validate_pdf_accepts_case_insensitive_media_type_with_parameters() -> None:
    result = asyncio.run(
        validate_pdf_upload(
            UploadStub(b"%PDF-1.7\n", content_type="Application/PDF; charset=binary"),
            max_size_bytes=1024,
        )
    )

    result.close()


def test_validate_pdf_rejects_wrong_signature() -> None:
    with pytest.raises(InvalidPdfSignatureError, match="signature"):
        asyncio.run(
            validate_pdf_upload(
                UploadStub(b"this is not a PDF"),
                max_size_bytes=1024,
            )
        )


def test_validate_pdf_stops_after_stream_exceeds_limit() -> None:
    upload = UploadStub(b"%PDF-1.7\n" + b"x" * 50)

    with pytest.raises(PdfTooLargeError, match="16-byte"):
        asyncio.run(
            validate_pdf_upload(
                upload,
                max_size_bytes=16,
                read_size_bytes=8,
            )
        )

    assert len(upload.read_sizes) == 3


@pytest.mark.parametrize("filename", [None, "", ".pdf", "paper.txt", "../..."])
def test_validate_pdf_rejects_invalid_filename(filename: str | None) -> None:
    with pytest.raises(InvalidPdfFilenameError):
        asyncio.run(
            validate_pdf_upload(
                UploadStub(b"%PDF-1.7\n", filename=filename),
                max_size_bytes=1024,
            )
        )


def test_sanitize_source_filename_removes_paths_controls_and_unsafe_characters() -> None:
    assert sanitize_source_filename("../folder/\x00draft:*? paper.PDF") == "_draft___ paper.PDF"


@pytest.mark.parametrize("separator", ["\uff0f", "\uff3c"])
def test_sanitize_source_filename_removes_separators_created_by_normalization(
    separator: str,
) -> None:
    assert sanitize_source_filename(f"folder{separator}evil.pdf") == "evil.pdf"


def test_sanitize_source_filename_replaces_unicode_format_controls() -> None:
    assert sanitize_source_filename("report\u202egnp.pdf") == "report_gnp.pdf"


def test_sanitize_source_filename_limits_length_and_preserves_pdf_suffix() -> None:
    sanitized = sanitize_source_filename(f"{'x' * 300}.pdf")

    assert len(sanitized) == 255
    assert sanitized.endswith(".pdf")
