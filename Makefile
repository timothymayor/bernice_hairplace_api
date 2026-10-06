.PHONY: setup dev worker up lint fmt typecheck test test-int parity openapi migrate seed check

setup:
	uv sync --all-groups
	uv run pre-commit install

dev:
	docker compose up -d redis
	uv run uvicorn app.main:create_app --factory --reload

worker:
	uv run arq app.workers.settings.WorkerSettings

up:
	docker compose up --build

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy app tests

test:
	uv run pytest -q

test-int:
	uv run pytest -q -m integration

parity:
	node scripts/export_ts_fixtures.mjs
	uv run pytest -q tests/parity

openapi:
	uv run python -m app.scripts.dump_openapi > openapi.json

# Staging/production migrations run only through CI (AGENTS.md §13).
migrate:
	supabase db push

seed:
	uv run python scripts/seed_catalog.py

check: lint typecheck test
