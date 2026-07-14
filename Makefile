.DEFAULT_GOAL := help

.PHONY: help setup infra up down backend-check frontend-check check test

help:
	@echo "EvidenceGraph development commands"
	@echo "  make setup          Install backend and frontend dependencies"
	@echo "  make infra          Start PostgreSQL, Redis, and MinIO"
	@echo "  make up             Build and start the complete Phase 0 stack"
	@echo "  make down           Stop the stack"
	@echo "  make check          Run formatting checks, linting, types, and tests"
	@echo "  make backend-check  Run all backend checks"
	@echo "  make frontend-check Run all frontend checks"

setup:
	@test -f .env || cp .env.example .env
	cd backend && uv sync --locked
	cd frontend && npm ci
	cd frontend && npx playwright install chromium

infra:
	docker compose up -d postgres redis minio

up:
	docker compose up --build

down:
	docker compose down

backend-check:
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .
	cd backend && uv run mypy app
	cd backend && uv run pytest
	cd backend && uv run alembic upgrade head

frontend-check:
	cd frontend && npm run format:check
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run test
	cd frontend && npm run build

check: backend-check frontend-check

test:
	cd backend && uv run pytest
	cd frontend && npm run test
