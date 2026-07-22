"""Configurable deterministic local token counting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

DEFAULT_TOKENIZER_NAME = "unicode_lexical_v1"
_TOKEN_PATTERN = re.compile(r"\w+(?:['\u2019-]\w+)*|[^\w\s]", flags=re.UNICODE)


@dataclass(frozen=True, slots=True)
class TokenSpan:
    """One lexical token and its character offsets."""

    text: str
    start: int
    end: int


class Tokenizer(Protocol):
    """Minimal tokenizer behavior required by the chunkers."""

    name: str

    def token_spans(self, text: str) -> tuple[TokenSpan, ...]: ...

    def count(self, text: str) -> int: ...

    def slice_tokens(self, text: str, start: int, end: int) -> str: ...


class UnicodeLexicalTokenizer:
    """Split Unicode words and punctuation without models or network access."""

    name = DEFAULT_TOKENIZER_NAME

    def token_spans(self, text: str) -> tuple[TokenSpan, ...]:
        return tuple(
            TokenSpan(text=match.group(0), start=match.start(), end=match.end())
            for match in _TOKEN_PATTERN.finditer(text)
        )

    def count(self, text: str) -> int:
        return sum(1 for _ in _TOKEN_PATTERN.finditer(text))

    def slice_tokens(self, text: str, start: int, end: int) -> str:
        spans = self.token_spans(text)
        if start < 0 or end < start or end > len(spans):
            raise ValueError("token slice is outside the available token range")
        if start == end:
            return ""
        return text[spans[start].start : spans[end - 1].end]


@lru_cache(maxsize=4)
def get_tokenizer(name: str = DEFAULT_TOKENIZER_NAME) -> Tokenizer:
    """Return a cached local tokenizer by its versioned configuration name."""
    if name == DEFAULT_TOKENIZER_NAME:
        return UnicodeLexicalTokenizer()
    raise ValueError(f"Unsupported tokenizer: {name}")
