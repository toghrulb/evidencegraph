# ADR 0001: Keep the application in a monorepo

- Status: Accepted
- Date: 2026-07-14

## Context

EvidenceGraph has a Next.js frontend, a FastAPI backend, local infrastructure definitions, future asynchronous workers, shared documentation, and end-to-end tests. A single product change will often cross more than one of these boundaries. The project also needs one reproducible local-development entry point and one CI view of product health.

## Decision

Keep all product components in one repository with explicit top-level ownership boundaries:

- `frontend/` for the Next.js application
- `backend/` for the FastAPI application and migrations
- `workers/` for future asynchronous worker entry points
- root-level Compose, environment, task-runner, and documentation files for cross-component concerns

Each application owns its dependencies, Dockerfile, checks, and tests. The root task runner and CI compose those checks without introducing a shared runtime dependency between applications.

## Consequences

Benefits:

- Cross-stack API and infrastructure changes can be reviewed and tested atomically.
- One checkout contains the complete local-development environment.
- Documentation and CI remain close to the code they describe.
- End-to-end tests can evolve alongside both applications.

Costs:

- CI must avoid rebuilding unaffected components unnecessarily as the repository grows.
- Dependency boundaries require discipline because proximity can encourage accidental coupling.
- Repository permissions and release workflows may need path-aware rules if separate teams own components later.

These costs are acceptable for a cohesive product and can be addressed with path filters and component-specific release jobs when build volume warrants them.
