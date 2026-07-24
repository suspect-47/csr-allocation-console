.PHONY: install lint typecheck test gate verify up down migrate fixtures web-install web-build

install:
	pip install -r requirements.txt

lint:
	ruff check app tests scripts

typecheck:
	mypy app

test:
	pytest -q

gate:
	python -m scripts.eval_gate

# Mirrors the Opsera gate (minus deploy). The stop-condition for local work.
verify: lint typecheck test

up:
	docker compose up --build

down:
	docker compose down -v

migrate:
	python -m scripts.migrate

# One-shot discovery run against the local stack.
discover:
	docker compose run --rm cron

fixtures:
	python -m scripts.record_fixtures

web-install:
	cd web && npm install

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run typecheck && npm run build
