# Architecture

## Phase 2 system

```text
FastAPI upload API
    | metadata                 | generated object key
    v                          v
PostgreSQL                   MinIO (original PDF)
    |                          ^
    | enqueue                  | load + parsed-schema-1.json
    v                          |
Redis -> Celery worker -> validate -> parse pages -> detect sections -> chunk
                              |
                              v
                      atomic chunk replacement
                              |
                              v
                     PostgreSQL (chunks + status)
```

Docker Compose provisions PostgreSQL/pgvector, Redis, MinIO, the FastAPI service, and the Celery worker. The API stores a validated original PDF and queues its generated document ID. The worker independently reloads and revalidates the stored bytes before extraction.

## Component boundaries

- `app/parsing/loader.py` verifies object existence, byte limits, and the stored `%PDF-` signature.
- `app/parsing/parser.py` uses PyMuPDF dictionary extraction to retain ordered layout blocks, font signals, page dimensions, and one-based page numbers.
- `app/parsing/normalization.py` conservatively repairs whitespace and obvious lowercase hyphen wraps while preserving paragraph and list boundaries.
- `app/parsing/sections.py` uses deterministic research-heading, numbering, font, bold, title-case, and spacing signals. It returns no heading when evidence is insufficient.
- `app/parsing/schemas.py` owns strict, immutable, versioned internal models. These models are independent from HTTP schemas.
- `app/chunking/tokenizer.py` owns the cached local tokenizer abstraction. The default `unicode_lexical_v1` counts Unicode words, contractions/hyphenated words, and punctuation without model downloads or network calls.
- `app/chunking/fixed.py` and `section_aware.py` define the two source-order grouping rules; `windowing.py` owns token windows and overlap.
- `app/chunking/persistence.py` atomically replaces a complete chunk set and finalizes document metadata.
- `app/ingestion/orchestrator.py` owns observable stage transitions and processing-attempt guards. The Celery task remains a thin adapter.

## Processing lifecycle

The compatible public `status` remains `uploaded`, `processing`, `ready`, or `failed`. The new `processing_stage` provides finer progress:

```text
uploaded -> processing -> parsing -> chunking -> ready
                                      \-------> failed
```

Every attempt receives a UUID. Stage writes and the final chunk transaction require that UUID to remain current, so an older worker cannot overwrite a newer retry. A successful retry deletes old chunks, inserts the complete new set, updates counts and versions, and marks the document ready in one database commit. A failed database commit rolls back the deletion and leaves the previous valid chunks intact. MinIO and PostgreSQL do not share a distributed transaction; the versioned parsed artifact may therefore already have been replaced if the database commit fails.

## Parsed intermediate and citation mapping

The complete `ParsedDocument` is serialized to a deterministic MinIO key ending in `parsed-schema-1.json`. PostgreSQL stores the generated key internally, but no API exposes it. This keeps page/block detail out of relational tables while retaining a replayable, testable artifact. Citation-facing chunks stay relational and include page range, section, source order, counts, strategy, configuration version, and parser/tokenizer metadata.

## Known limitations

- Image-only/scanned PDFs produce a controlled `no_extractable_text` failure; Phase 2 has no OCR.
- PyMuPDF block ordering can be imperfect for complex multi-column layouts.
- Tables, figures, and equations are extracted only as ordinary available text; structure and visual meaning are not interpreted.
- Section detection is heuristic and may miss or misclassify unusual headings.
- The local lexical token count is deterministic but does not claim parity with a future embedding or LLM tokenizer.

See [ADR 0001](decisions/0001-monorepo.md) and [ADR 0002](decisions/0002-phase2-parsing-chunking.md).
