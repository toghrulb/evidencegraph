# Phase 2 implementation notes

The worker processes each upload as a complete attempt: claim, validate/load, parse, store the versioned parsed representation, chunk, and atomically persist. Public status remains compatible with Phase 1 while `processing_stage` exposes current work.

Fixed-token chunking normally keeps pages separate. It crosses into the next page only when the pending page has fewer than `MINIMUM_CHUNK_SIZE` tokens. Section-aware chunking groups consecutive paragraphs under their nearest detected title and never combines differing logical sections merely to fill a window. Oversized groups are split deterministically with overlap constrained to that group.

All tests generate small original PDFs programmatically. No paper corpus, hosted tokenizer, model download, external API, OCR engine, embedding model, or retrieval framework is used.

Text normalization removes non-printable PDF extraction artifacts, including null bytes that PostgreSQL cannot store, while preserving tabs, line breaks, paragraph boundaries, and printable Unicode content.

Known limitations are image-only documents, complex columns, tables, figures/equations, and heuristic headings. These are reported or documented rather than represented as solved.
