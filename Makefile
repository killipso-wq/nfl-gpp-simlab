.PHONY: help install dev lint format type test test-cov

help:
	@echo "Targets: install, dev, lint, format, type, test, test-cov"

install:
	python -m pip install --upgrade pip
	pip install -e .

dev: install
	pip install '.[dev]'

lint:
	ruff check .

format:
	black .
	ruff format . || true

type:
	mypy src

test:
	pytest

test-cov:
	pytest --cov=nfl_gpp_simlab --cov-report=term-missing