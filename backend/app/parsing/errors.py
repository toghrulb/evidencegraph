"""Controlled errors produced by the Phase 2 document processor."""

from __future__ import annotations


class DocumentProcessingError(RuntimeError):
    """Base error with safe user text and a stable technical code."""

    code = "document_processing_error"
    user_message = "The document could not be processed."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.user_message)


class StoredPdfMissingError(DocumentProcessingError):
    code = "stored_pdf_missing"
    user_message = "The stored PDF could not be found."


class StoredPdfReadError(DocumentProcessingError):
    code = "stored_pdf_read_error"
    user_message = "The stored PDF could not be read."


class StoredPdfTooLargeError(DocumentProcessingError):
    code = "stored_pdf_too_large"
    user_message = "The stored PDF exceeds the configured processing size limit."


class InvalidStoredPdfSignatureError(DocumentProcessingError):
    code = "invalid_stored_pdf_signature"
    user_message = "The stored file does not have a valid PDF signature."


class CorruptPdfError(DocumentProcessingError):
    code = "corrupt_pdf"
    user_message = "The PDF is corrupted or unreadable."


class EncryptedPdfError(DocumentProcessingError):
    code = "encrypted_pdf"
    user_message = "Encrypted or password-protected PDFs are not supported."


class PdfPageLimitError(DocumentProcessingError):
    code = "pdf_page_limit_exceeded"
    user_message = "The PDF exceeds the configured page-count limit."


class NoExtractableTextError(DocumentProcessingError):
    code = "no_extractable_text"
    user_message = "The PDF contains no extractable text; scanned PDFs require OCR."


class ParsedIntermediateStorageError(DocumentProcessingError):
    code = "parsed_intermediate_storage_error"
    user_message = "The parsed document could not be saved for retryable processing."


class StaleProcessingAttemptError(DocumentProcessingError):
    code = "stale_processing_attempt"
    user_message = "A newer processing attempt has replaced this job."


class UnexpectedProcessingError(DocumentProcessingError):
    code = "unexpected_processing_error"
    user_message = "The document could not be processed due to an internal error."
