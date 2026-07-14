# Implementation plan

EvidenceGraph is delivered in ordered phases. A later phase must not begin while earlier acceptance criteria are failing.

## Current implementation: Phase 0

The repository foundation consists of:

1. A backend/frontend monorepo structure with reserved directories for future workers, evaluation data, sample papers, and scripts.
2. Pinned local PostgreSQL with pgvector, Redis, and MinIO services in Docker Compose.
3. A FastAPI application with liveness and lifecycle-readiness probes plus endpoint tests.
4. A basic Next.js landing page.
5. Ruff, mypy, pytest, ESLint, Prettier, TypeScript, Playwright, and production-build checks.
6. GitHub Actions jobs for backend checks, frontend checks, and Compose-model validation.
7. Documented environment variables and exact local startup commands.

Phase 0 is considered verified only when the checks documented in `README.md` pass from a clean dependency installation and `docker compose config --quiet` validates the service model.

## Deferred phases

- **Phase 1:** collection metadata, PDF upload, object storage, and ingestion status.
- **Phase 2:** page-aware parsing and fixed-token/section-aware chunking.
- **Phase 3:** embeddings, pgvector persistence, and dense retrieval.
- **Phase 4:** BM25, reciprocal-rank fusion, reranking, and diagnostics.
- **Phase 5:** streamed grounded generation and validated citations.
- **Phase 6:** research workspace, evidence panel, and PDF navigation.
- **Phase 7:** paper comparison, versioned evaluation data, metrics, and MLflow.
- **Phase 8:** reliability, security hardening, integration/E2E coverage, and deployment readiness.

The detailed requirements and acceptance criteria for every phase remain in `AGENTS.md`. This document does not relax or replace them.
