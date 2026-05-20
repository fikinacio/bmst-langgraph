.PHONY: install run test lint docker-up docker-down

install:
	pip install -e ".[dev]"

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

docker-up:
	docker compose up -d

docker-down:
	docker compose down
