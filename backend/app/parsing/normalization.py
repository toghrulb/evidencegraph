"""Conservative text normalization that preserves document structure."""

from __future__ import annotations

import re

_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\r\n]+")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")
_LIST_MARKER = re.compile(r"^(?:[-*\u2022\u25aa\u2014\u2023]|\d+[.)]|[A-Za-z][.)])\s+")
_LOWERCASE_WORD_END = re.compile(r"[a-z]-$")
_LOWERCASE_WORD_START = re.compile(r"^[a-z]")
_UNSUPPORTED_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_inline_whitespace(text: str) -> str:
    """Remove extraction artifacts and collapse horizontal whitespace."""
    cleaned = _UNSUPPORTED_CONTROL_CHARACTERS.sub("", text)
    return _HORIZONTAL_WHITESPACE.sub(" ", cleaned.replace("\u00a0", " ")).strip()


def normalize_paragraph(text: str) -> str:
    """Repair safe line wraps inside one layout block."""
    lines = [normalize_inline_whitespace(line) for line in text.replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return ""

    output: list[str] = []
    for line in lines:
        if not output:
            output.append(line)
            continue

        previous = output[-1]
        if _LIST_MARKER.match(line):
            output.append(line)
        elif _LOWERCASE_WORD_END.search(previous) and _LOWERCASE_WORD_START.match(line):
            output[-1] = previous[:-1] + line
        elif _LIST_MARKER.match(previous):
            output[-1] = f"{previous} {line}"
        else:
            output[-1] = f"{previous} {line}"

    return "\n".join(output)


def normalize_text(text: str) -> str:
    """Normalize paragraphs independently and retain blank-line boundaries."""
    normalized_newlines = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [
        normalize_paragraph(value) for value in _PARAGRAPH_BREAK.split(normalized_newlines)
    ]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
