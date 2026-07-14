# Architecture

## Phase 0 system

Phase 0 establishes independently testable frontend and backend applications plus the stateful services required by later phases.

```text
Browser :3000
    |
    v
Next.js frontend

FastAPI backend :8000
    |          |          |
    v          v          v
PostgreSQL   Redis      MinIO
+ pgvector   :6379      :9000
:5432                    console :9001
```

Docker Compose is the local orchestration boundary. It provides pinned PostgreSQL/pgvector, Redis, and MinIO images and builds the two application containers from their own Dockerfiles. Named volumes retain local service data between container restarts.

The FastAPI process currently exposes liveness and lifecycle-readiness probes. Phase 0 does not yet open connections to PostgreSQL, Redis, or MinIO, so readiness deliberately does not pretend to validate those dependencies.

## Component boundaries

- `frontend/` owns browser rendering and frontend tests. Its Phase 0 responsibility is a responsive landing page and no application data flow.
- `backend/` owns HTTP APIs and backend tests. Its Phase 0 contract consists only of `/health/live`, `/health/ready`, and generated OpenAPI documentation.
- PostgreSQL with pgvector is provisioned now for future metadata and vector storage.
- Redis is provisioned now for the future Celery queue and transient coordination.
- MinIO is provisioned now for future original-PDF storage. Bucket lifecycle is intentionally deferred until the storage integration is implemented.

## Planned target architecture

Later phases will introduce the ingestion and query paths described in `AGENTS.md`: asynchronous workers will extract and chunk papers, PostgreSQL will store metadata and vectors, and the backend will combine dense and sparse retrieval before grounded answer generation. These are architectural constraints, not functionality claimed by Phase 0.

The main design decision for the repository boundary is recorded in [ADR 0001](decisions/0001-monorepo.md).
