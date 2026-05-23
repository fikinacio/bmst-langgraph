.PHONY: install run run-scheduler run-api run-all test test-all lint docker-up docker-down db-migrate

install:
	pip install -e ".[dev]"

# ── Local development ─────────────────────────────────────────────────────────

run: run-api

run-api:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-scheduler:
	python -m src.scheduler.cron

run-all:
	# Run api and scheduler in parallel (for local dev only — use docker-compose in prod)
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 & python -m src.scheduler.cron

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

test-all:
	pytest tests/ -v --tb=short

# ── Lint ──────────────────────────────────────────────────────────────────────

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# ── Database ──────────────────────────────────────────────────────────────────

db-migrate:
	@echo "Applying Supabase schema migrations..."
	@echo "Run SQL files in docs/schema/ manually via the Supabase dashboard or psql."
	@echo "See architecture.md for the full schema definition."
