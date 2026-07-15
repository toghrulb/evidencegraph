"""Validation for PDF uploads before persistence or object-storage writes."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from tempfile import SpooledTemporaryFile
from types import TracebackType
from typing import Protocol, Self

PDF_CONTENT_TYPE = "application/pdf"
PDF_SIGNATURE = b"%PDF-"
DEFAULT_READ_SIZE_BYTES = 64 * 1024
DEFAULT_SPOOL_SIZE_BYTES = 1024 * 1024
MAX_SOURCE_FILENAME_LENGTH = 255

_UNSAFE_FILENAME_CHARACTERS = re.compile(r'[:*?"<>|]')
_WHITESPACE = re.compile(r"\s+")


class UploadSource(Protocol):
    """The subset of FastAPI's ``UploadFile`` used by the validator."""

    filename: str | None
    content_type: str | None

    async def read(self, size: int = -1) -> bytes: ...


class PdfValidationError(ValueError):
    """Base class for controlled, user-correctable PDF validation failures."""

    code = "invalid_pdf"


class InvalidPdfMediaTypeError(PdfValidationError):
    """Raised when the declared upload media type is not PDF."""

    code = "invalid_pdf_media_type"


class InvalidPdfFilenameError(PdfValidationError):
    """Raised when the source filename is missing or is not a PDF filename."""

    code = "invalid_pdf_filename"


class InvalidPdfSignatureError(PdfValidationError):
    """Raised when uploaded bytes do not begin with the PDF signature."""

    code = "invalid_pdf_signature"


class PdfTooLargeError(PdfValidationError):
    """Raised as soon as a streamed upload exceeds its configured size limit."""

    code = "pdf_too_large"


@dataclass(slots=True)
class ValidatedPdf:
    """A validated, rewindable PDF and metadata derived from its bytes."""

    source_filename: str
    size_bytes: int
    checksum: str
    file: SpooledTemporaryFile[bytes]
    content_type: str = PDF_CONTENT_TYPE

    def close(self) -> None:
        """Release memory or the temporary file backing this upload."""

        self.file.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def sanitize_source_filename(filename: str | None) -> str:
    """Return a display-safe basename while retaining a human-readable name."""

    if not filename:
        raise InvalidPdfFilenameError("A PDF filename is required.")

    normalized_path = unicodedata.normalize("NFKC", filename)
    normalized = normalized_path.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    normalized = "".join(
        "_" if unicodedata.category(character).startswith("C") else character
        for character in normalized
    )
    normalized = _UNSAFE_FILENAME_CHARACTERS.sub("_", normalized)
    normalized = _WHITESPACE.sub(" ", normalized).strip(" .")

    if not normalized:
        raise InvalidPdfFilenameError("A valid PDF filename is required.")
    if not normalized.lower().endswith(".pdf"):
        raise InvalidPdfFilenameError("The uploaded filename must end with .pdf.")
    if not normalized[:-4].strip(" ._"):
        raise InvalidPdfFilenameError("The uploaded PDF filename must include a name.")

    if len(normalized) > MAX_SOURCE_FILENAME_LENGTH:
        suffix = normalized[-4:]
        normalized = normalized[: MAX_SOURCE_FILENAME_LENGTH - len(suffix)].rstrip(" .") + suffix

    return normalized


async def validate_pdf_upload(
    upload: UploadSource,
    *,
    max_size_bytes: int,
    spool_size_bytes: int = DEFAULT_SPOOL_SIZE_BYTES,
    read_size_bytes: int = DEFAULT_READ_SIZE_BYTES,
) -> ValidatedPdf:
    """Stream, validate, hash, and rewind one uploaded PDF.

    The upload is never loaded into memory as one byte string. Small PDFs remain
    memory-backed and larger PDFs transparently roll over to a temporary file.
    """

    if max_size_bytes <= 0:
        raise ValueError("max_size_bytes must be positive")
    if spool_size_bytes <= 0:
        raise ValueError("spool_size_bytes must be positive")
    if read_size_bytes <= 0:
        raise ValueError("read_size_bytes must be positive")

    media_type = (upload.content_type or "").partition(";")[0].strip().lower()
    if media_type != PDF_CONTENT_TYPE:
        raise InvalidPdfMediaTypeError("Only application/pdf uploads are accepted.")

    source_filename = sanitize_source_filename(upload.filename)
    stream = SpooledTemporaryFile[bytes](max_size=min(spool_size_bytes, max_size_bytes), mode="w+b")
    checksum = hashlib.sha256()
    size_bytes = 0

    try:
        while chunk := await upload.read(read_size_bytes):
            size_bytes += len(chunk)
            if size_bytes > max_size_bytes:
                raise PdfTooLargeError(
                    f"The PDF exceeds the configured {max_size_bytes}-byte upload limit."
                )
            checksum.update(chunk)
            stream.write(chunk)

        stream.seek(0)
        if stream.read(len(PDF_SIGNATURE)) != PDF_SIGNATURE:
            raise InvalidPdfSignatureError("The uploaded file does not have a valid PDF signature.")
        stream.seek(0)

        return ValidatedPdf(
            source_filename=source_filename,
            size_bytes=size_bytes,
            checksum=checksum.hexdigest(),
            file=stream,
        )
    except BaseException:
        stream.close()
        raise
