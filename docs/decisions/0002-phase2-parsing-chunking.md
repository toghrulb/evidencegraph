# ADR 0002: Explicit PyMuPDF parsing and versioned local chunking

- Status: Accepted
- Date: 2026-07-16

## Context

Phase 2 needs page-aware extraction, deterministic section heuristics, retryable intermediate data, and token-bounded chunks without pulling Phase 3 model or retrieval concerns into the worker.

## Decision

Use PyMuPDF directly and request dictionary-form page text. Its block/span structure supplies bounding boxes, font sizes, font flags, and source-page dimensions needed by the deterministic section detector. Extraction is passive; EvidenceGraph does not execute document actions or embedded content.

Store one immutable `ParsedDocument` JSON representation at a generated, schema-versioned MinIO key. Store final chunks in PostgreSQL because they need relational ordering, cascade deletion, and future citation joins. The intermediate key remains internal.

Detect headings from common research-paper titles, numbered-title patterns, block length, font size relative to the document median, bold flags, title case, and preceding space. When signals are insufficient, keep the section null; never invent a title.

Use the project-owned `unicode_lexical_v1` tokenizer. It is small, deterministic, cached, offline, and sufficient to enforce Phase 2 token bounds. A named abstraction allows a later version to align with a selected embedding model without rewriting chunkers.

Persist `PARSER_VERSION`, `CHUNKING_CONFIG_VERSION`, tokenizer name, and active numeric bounds with outputs. Changing behavior requires advancing the relevant version rather than silently changing provenance.

Assign every processing attempt a UUID. Stage changes and final persistence require the current UUID. Generate the full parsed document and chunk list before beginning the final database transaction; then delete old chunks, insert the new set, update counts/status, and commit together. Rollback preserves the previous valid set if insertion fails, and a redelivered completed task is a no-op.

## Consequences

The pipeline is explicit, testable, and has no model/network dependency. Parsed JSON and database writes cannot be one distributed transaction, so a failed database commit may leave a newer deterministic intermediate at the same versioned key. OCR, visual/table understanding, and perfect reading order or heading detection remain outside this decision.
