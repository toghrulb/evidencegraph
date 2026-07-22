# EvidenceGraph backend

The Python 3.12 backend uses FastAPI, SQLAlchemy/Alembic, PostgreSQL, MinIO, Redis/Celery, and PyMuPDF. Phase 2 processes originals into versioned parsed JSON and page-aware chunks; it has no embeddings or retrieval.

From the repository root, start infrastructure:

```powershell
docker compose up -d postgres redis minio
```

Then run the API and migrations:

```powershell
Set-Location backend
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Run the worker in another terminal (`--pool=solo` is appropriate on Windows):

```powershell
Set-Location backend
uv run celery -A app.worker:celery_app worker --loglevel=INFO --pool=solo
```

Checks:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest
```

See the root README, `docs/environment.md`, and `docs/phase-2.md` for configuration and behavior.
