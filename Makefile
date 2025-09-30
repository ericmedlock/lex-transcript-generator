# Performance-Enhanced LLM Generator Makefile

.PHONY: help install migrate run bench test clean

help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  migrate    - Apply database migrations"
	@echo "  run        - Start performance generator"
	@echo "  bench      - Run benchmark"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean up temporary files"

install:
	pip install -r requirements.txt

migrate:
	@if [ -z "$(PERF_DB_URL)" ]; then \
		echo "Error: PERF_DB_URL environment variable not set"; \
		exit 1; \
	fi
	python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('$(PERF_DB_URL)').execute(open('db/migrations/001_perf.sql').read()))"

run:
	python -m src.perf_generator

bench:
	python -m src.bench $(ARGS)

test:
	pytest tests/perf/ -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +