# Alembic migrations

The Phase 1 revision creates the `collections` and `documents` metadata tables. Run
`uv run alembic upgrade head` after PostgreSQL is available. Docker Compose applies
the migration automatically before starting the API.

Later phases must add new revisions rather than editing an already-shared migration.
