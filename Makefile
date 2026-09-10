.PHONY: up down test lint

up:
	docker compose up --build

down:
	docker compose down

test:
	pytest -q

lint:
	ruff check .
