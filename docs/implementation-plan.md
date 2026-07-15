# Implementation plan

EvidenceGraph is delivered in ordered phases. A later phase must not begin while earlier acceptance criteria are failing.

## Current implementation: Phase 1

Phase 1 adds the following to the verified Phase 0 foundation:

1. SQLAlchemy 2 collection/document models and an Alembic migration for PostgreSQL.
2. Collection create, list, fetch, and delete APIs.
3. Streamed PDF MIME, extension, signature, and size validation with filename sanitization and SHA-256 hashing.
4. Original-file upload, streaming download, and deletion through a MinIO-compatible storage interface.
5. Document metadata, collection-scoped duplicate detection in both application logic and a database constraint, and generated storage keys.
6. Redis/Celery dispatch plus an idempotent `uploaded` to `processing` status transition.
7. Unit and API tests using isolated local dependencies, and a gated full-stack test covering PostgreSQL, MinIO, Redis, Celery, and FastAPI.
8. CI jobs for backend/frontend checks, Compose validation, migration SQL generation, and the full Phase 1 integration flow.

Phase 1 is verified only when the documented static checks and tests pass and the Compose integration test observes a real worker transition to `processing`.

## Deferred phases

- **Phase 2:** page-aware parsing and fixed-token/section-aware chunking; this phase will complete processing and may mark documents `ready`.
- **Phase 3:** embeddings, pgvector persistence, and dense retrieval.
- **Phase 4:** BM25, reciprocal-rank fusion, reranking, and diagnostics.
- **Phase 5:** streamed grounded generation and validated citations.
- **Phase 6:** research workspace, upload UI, evidence panel, and PDF navigation.
- **Phase 7:** paper comparison, versioned evaluation data, metrics, and MLflow.
- **Phase 8:** rate limits, broader reliability hardening, demo data, and deployment readiness.

The detailed requirements and final MVP acceptance criteria remain in `AGENTS.md`. This document does not relax or replace them.
