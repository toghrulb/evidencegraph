# Architecture

## Phase 1 system

```text
Browser :3000
    |
    v
Next.js frontend

FastAPI backend :8000
    |              | enqueue       | original PDFs
    v              v               v
PostgreSQL       Redis           MinIO
metadata          |              :9000
:5432             v
             Celery worker
             uploaded -> processing
```

Docker Compose is the local orchestration boundary. It provisions pinned PostgreSQL/pgvector, Redis, and MinIO images and builds the frontend, API, and worker containers. The backend applies the Alembic migration before serving traffic. Named volumes retain local service data.

## Component boundaries

- `backend/app/models` owns SQLAlchemy collection/document metadata. The first migration creates only those Phase 1 tables.
- `backend/app/documents` validates uploads without reading an entire PDF into memory. It calculates SHA-256 while copying into a spooled temporary file.
- `backend/app/storage` is a narrow provider-neutral contract with a MinIO-compatible S3 implementation. HTTP routes never construct user-controlled storage paths.
- `backend/app/ingestion` owns queue dispatch and the idempotent status claim. Phase 1 does not contain extraction or other processing logic.
- `backend/app/api` exposes versioned collection/document contracts and maps controlled validation or dependency failures to HTTP responses.
- PostgreSQL enforces document status values, referential integrity, globally unique storage keys, and collection-scoped checksum uniqueness.
- The Next.js application remains the Phase 0 landing page. The upload and research workspace UI belongs to Phase 6 in the project specification.

## Upload transaction boundary

```text
validate + hash PDF
        |
check collection/checksum
        |
upload generated key to MinIO
        |
commit document metadata
        |
enqueue Celery job
        |
worker claims uploaded -> processing
```

Uploads and collection deletion take a PostgreSQL row lock on the parent collection so a concurrent upload cannot commit an untracked object while that collection is being removed. If the metadata insert loses a duplicate race, the just-uploaded unique object is removed. If queue publication fails after the metadata commit, the row is retained and marked `failed`, making the failure observable. Object storage and PostgreSQL cannot share a distributed transaction; delete operations therefore remove stored objects before committing metadata deletion and report storage failures instead of silently orphaning known objects.

## Deliberate Phase 1 limit

`processing` means the asynchronous handoff was accepted. It does not mean extraction has completed. Page extraction, chunking, embeddings, retrieval, and generation are absent, and no Phase 1 code marks a document `ready`.

The monorepo boundary is recorded in [ADR 0001](decisions/0001-monorepo.md).
