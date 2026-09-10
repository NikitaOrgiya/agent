.PHONY: venv install test lint migrate revision run up down

VENV_PY ?= .venv/bin/python

venv:
	python -m venv .venv

install:
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -e ".[dev]"

test:
	$(VENV_PY) -m pytest -q

lint:
	$(VENV_PY) -m ruff check .

migrate:
	$(VENV_PY) -m alembic upgrade head

revision:
	$(VENV_PY) -m alembic revision --autogenerate -m "$(m)"

run:
	$(VENV_PY) -m uvicorn app.main:app --host 127.0.0.1 --port 8080

up:
	docker compose up --build

down:
	docker compose down
