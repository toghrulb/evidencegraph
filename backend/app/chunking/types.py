"""Shared Phase 2 chunking types."""

from enum import StrEnum


class ChunkingStrategy(StrEnum):
    """Selectable project-owned chunking strategies."""

    FIXED_TOKEN = "fixed_token"
    SECTION_AWARE = "section_aware"
