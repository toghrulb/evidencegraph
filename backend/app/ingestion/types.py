"""Processing lifecycle types that preserve the Phase 1 status contract."""

from enum import StrEnum


class ProcessingStage(StrEnum):
    """Detailed stage within the stable public document status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSING = "parsing"
    CHUNKING = "chunking"
    READY = "ready"
    FAILED = "failed"
