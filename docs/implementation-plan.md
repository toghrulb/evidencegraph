# Implementation plan

EvidenceGraph is delivered in ordered phases. Phase 0 and Phase 1 remain intact; Phase 2 is the current implementation boundary.

## Current implementation: Phase 2

Phase 2 provides:

1. Stored-object existence, signature, byte-size, encryption, corruption, and page-limit validation.
2. PyMuPDF page-by-page dictionary extraction with versioned typed document/page/block/paragraph models.
3. Conservative whitespace normalization, empty-page warnings, one-based page metadata, and deterministic section-title heuristics.
4. A versioned parsed-document JSON artifact in MinIO for inspectability and retry support.
5. A configurable cached local tokenizer with no hidden downloads.
6. Fixed-token and section-aware token-bounded chunking with paragraph preference, overlap, page ranges, source order, configuration provenance, and deterministic output.
7. Relational chunks with cascade deletion and indexed document, page, order, and strategy fields.
8. An attempt-guarded Celery workflow and atomic chunk replacement that prevents duplicate chunks on retries.
9. Extended document/status APIs plus a paginated chunk diagnostic route.
10. Unit, database-backed integration, worker-boundary, and gated real-Compose tests.

Phase 2 is verified only when migrations apply from an empty database and formatting, lint, mypy, unit/API tests, real Compose integration, and unchanged frontend checks pass.

## Deferred phases

- **Phase 3:** embeddings, pgvector persistence, and dense retrieval.
- **Phase 4:** BM25, reciprocal-rank fusion, reranking, and retrieval diagnostics.
- **Phase 5:** streamed grounded generation and validated citations.
- **Phase 6:** research workspace, upload UI, evidence panel, and PDF navigation.
- **Phase 7:** paper comparison, evaluation data, metrics, and MLflow.
- **Phase 8:** broader reliability hardening and deployment readiness.

No Phase 3 embeddings or retrieval behavior is present. Detailed requirements remain in `AGENTS.md`.
