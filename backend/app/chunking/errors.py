"""Controlled failures from transactional chunk persistence."""

from app.parsing.errors import DocumentProcessingError


class ChunkPersistenceError(DocumentProcessingError):
    """Raised when a complete replacement chunk set cannot be committed."""

    code = "chunk_persistence_error"
    user_message = "The generated chunks could not be saved."
