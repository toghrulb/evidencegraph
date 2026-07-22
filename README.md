# EvidenceGraph

EvidenceGraph is a research-intelligence platform for answering questions across technical papers with inspectable evidence and page-level citations.

The repository currently implements **Phases 0–2**. Users can manage collections, upload validated PDFs, retain originals in MinIO, and asynchronously produce page-aware, section-aware chunks. Embeddings, retrieval, answer generation, and the research workspace remain intentionally absent until later phases.

## Prerequisites

- Docker Engine 24+ with Docker Compose v2
- Python 3.12 and [uv](https://docs.astral.sh/uv/) for native backend development
- Node.js 24 and npm 10+ for native frontend development
- GNU Make is optional; every Make target has an equivalent command below

## Start the Phase 2 stack

From the repository root, create a local environment file once:

```powershell
Copy-Item .env.example .env
```

Build, migrate, and start the applications and infrastructure:

```powershell
docker compose up --build -d --wait --wait-timeout 300
```

The backend container applies `alembic upgrade head` before it starts. The worker then consumes Celery jobs from Redis.

Open:

- Frontend: <http://localhost:3000>
- API documentation: <http://localhost:8000/docs>
- API liveness: <http://localhost:8000/health/live>
- API readiness: <http://localhost:8000/health/ready>
- MinIO console: <http://localhost:9001>

Inspect or stop the stack with:

```powershell
docker compose ps
docker compose logs backend worker
docker compose down
```

The credentials in `.env.example` are local-only defaults. Change them before exposing the stack on a shared network, and never commit `.env`.

## Phase 2 processing and API

The main endpoints are:

```text
POST   /api/v1/collections
GET    /api/v1/collections
GET    /api/v1/collections/{collection_id}
DELETE /api/v1/collections/{collection_id}

POST   /api/v1/collections/{collection_id}/documents
GET    /api/v1/collections/{collection_id}/documents
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/status
GET    /api/v1/documents/{document_id}/file
GET    /api/v1/documents/{document_id}/chunks
DELETE /api/v1/documents/{document_id}
```

Uploads use `multipart/form-data`: `file` is required, while `title`, repeated `authors`, `publication_year`, and `chunking_strategy` (`fixed_token` or `section_aware`) are optional. Only an `application/pdf` upload with a `.pdf` filename and `%PDF-` byte signature is accepted. The worker independently checks the stored signature, configured byte/page limits, encryption, and readability.

A new document progresses asynchronously through `uploaded → processing → parsing → chunking → ready`. Public `status` keeps the Phase 1 values while `processing_stage` exposes detailed progress. Controlled failures become `failed` with a safe message and technical code. Parsed page/block/paragraph metadata is stored as versioned JSON in MinIO; complete chunk sets are replaced atomically in PostgreSQL so retries do not duplicate rows.

The default `unicode_lexical_v1` tokenizer is deterministic and local: no model is downloaded during processing or tests. Chunk limits and behavior are configured through the variables documented in [docs/environment.md](docs/environment.md).

## Native backend development

Start the stateful services:

```powershell
docker compose up -d postgres redis minio
```

Run migrations and the API:

```powershell
Set-Location backend
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Run the worker in another terminal. On Windows, use Celery's solo pool:

```powershell
Set-Location backend
uv run celery -A app.worker:celery_app worker --loglevel=INFO --pool=solo
```

Run the frontend in another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

## Checks

Backend formatting, linting, type checking, unit/API tests, and migration:

```powershell
Set-Location backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
uv run alembic upgrade head
```

Frontend checks remain unchanged in Phase 1:

```powershell
Set-Location frontend
npm run format:check
npm run lint
npm run typecheck
npx playwright install chromium
npm run test
npm run build
```

Run the real Phase 2 integration test against the rebuilt stack:

```powershell
docker compose up --build -d postgres redis minio backend worker --wait --wait-timeout 300
Set-Location backend
$env:RUN_INTEGRATION_TESTS = "1"
uv run pytest tests/integration
Remove-Item Env:RUN_INTEGRATION_TESTS
```

With GNU Make, `make setup`, `make infra`, `make up`, `make check`, `make integration`, and `make down` provide root-level equivalents.

## Repository layout

```text
backend/            FastAPI, SQLAlchemy/Alembic, Celery, storage adapters, and tests
frontend/           Next.js application and browser tests
workers/            Reserved for worker-specific deployment assets
evaluation_data/    Reserved for version-controlled evaluation datasets
sample_papers/      Reserved for redistributable test papers
scripts/            Reserved for project automation
docs/               Architecture, API notes, plans, and decisions
.github/workflows/  Static checks and full-stack Phase 2 integration CI
```

See [the architecture overview](docs/architecture.md), [the implemented API](docs/api.md), [the environment reference](docs/environment.md), [the Phase 2 notes](docs/phase-2.md), [the implementation plan](docs/implementation-plan.md), and [ADR 0002](docs/decisions/0002-phase2-parsing-chunking.md).

`AGENTS.md` remains the canonical project specification. `CLAUDE.md` points to it so the two instruction entry points cannot drift.
