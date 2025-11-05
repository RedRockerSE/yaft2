# Makefile for YAFT project

.PHONY: help venv install install-dev test lint format clean build run

help:
	@echo "YAFT - Yet Another Forensic Tool"
	@echo ""
	@echo "Available targets:"
	@echo "  venv          Create virtual environment with uv"
	@echo "  install       Install production dependencies with uv"
	@echo "  install-dev   Install development dependencies with uv"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with ruff"
	@echo "  typecheck     Run type checking with mypy"
	@echo "  clean         Clean build artifacts and cache"
	@echo "  build         Build executable for current platform"
	@echo "  build-clean   Clean build and rebuild executable"
	@echo "  run           Run the application from source"

venv:
	uv venv

install:
	uv pip install -r requirements.txt

install-dev:
	uv pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src/ tests/ plugins/

format:
	ruff format src/ tests/ plugins/

typecheck:
	mypy src/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:
	python build.py

build-clean:
	python build.py --clean

run:
	python -m yaft.cli
