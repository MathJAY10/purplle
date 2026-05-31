COMPOSE ?= docker compose

.PHONY: up down logs test lint pipeline worker

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

test:
	python -m pytest -q

lint:
	python -m compileall app tests

worker:
	python -m app.workers.run_worker

pipeline:
	python -m app.cv.run_pipeline