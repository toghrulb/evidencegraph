FROM ghcr.io/astral-sh/uv:0.11.26 AS uv

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN groupadd --system evidencegraph \
    && useradd --system --gid evidencegraph --home-dir /app evidencegraph \
    && chown -R evidencegraph:evidencegraph /app

USER evidencegraph

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]

