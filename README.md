# EvidenceGraph

EvidenceGraph is a research-intelligence platform designed to answer questions across technical papers with inspectable retrieval evidence and page-level citations.

This repository currently implements **Phase 0 only**: the monorepo foundation, local infrastructure, FastAPI health probes, a basic Next.js landing page, automated checks, and CI. Document ingestion, retrieval, generation, citations, and all other RAG behavior belong to later phases and are intentionally absent.

## Prerequisites

- Docker Engine 24+ with Docker Compose v2
- Python 3.12 and [uv](https://docs.astral.sh/uv/) for native backend development
- Node.js 24 and npm 10+ for native frontend development
- GNU Make is optional; every Make target has an equivalent command below

## Start the complete Phase 0 stack

From the repository root, create a local environment file and build all services:

```bash
cp .env.example .env
docker compose up --build
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Then open:

- Frontend: <http://localhost:3000>
- API documentation: <http://localhost:8000/docs>
- API liveness: <http://localhost:8000/health/live>
- API readiness: <http://localhost:8000/health/ready>
- MinIO console: <http://localhost:9001>

Stop the stack with:

```bash
docker compose down
```

The credentials in `.env.example` are deliberately local-only defaults. Change them before using any shared or remotely reachable environment. Do not commit `.env`.

## Native development

Start only the stateful infrastructure:

```bash
docker compose up -d postgres redis minio
```

Run the backend in a separate terminal:

```bash
cd backend
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Run the frontend in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The current readiness endpoint reports completion of the FastAPI lifecycle only. Database, Redis, and object-storage dependency probes will be added with the features that consume those services.

## Run all checks

Backend formatting, linting, type checking, and tests:

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
uv run alembic upgrade head
```

Frontend formatting, linting, type checking, tests, and production build:

```bash
cd frontend
npm run format:check
npm run lint
npm run typecheck
npx playwright install chromium
npm run test
npm run build
```

With GNU Make, `make setup`, `make infra`, `make up`, `make check`, and `make down` provide root-level equivalents. The first browser installation may download Playwright's Chromium build.
Developers who already have Google Chrome installed may instead set `PLAYWRIGHT_CHANNEL=chrome` when running the browser tests.

## Configuration

`.env.example` documents every required application variable and safe local defaults. `LLM_PROVIDER=none` and an empty `LLM_API_KEY` are intentional: no hosted model is required for Phase 0. Later ingestion and retrieval phases must continue to operate without a hosted LLM key.

## Repository layout

```text
backend/            FastAPI application, Alembic scaffold, and tests
frontend/           Next.js application and browser tests
workers/            Reserved for asynchronous workers in a later phase
evaluation_data/    Reserved for version-controlled evaluation datasets
sample_papers/      Reserved for redistributable test papers
scripts/            Reserved for project automation
docs/               Architecture, API notes, plans, and decisions
.github/workflows/  Continuous integration
```

See [the architecture overview](docs/architecture.md), [the implemented API](docs/api.md), [the implementation plan](docs/implementation-plan.md), and [ADR 0001](docs/decisions/0001-monorepo.md).

`AGENTS.md` is the canonical implementation specification. `CLAUDE.md` points to it instead of duplicating policy text, preventing the two instruction entry points from drifting.
