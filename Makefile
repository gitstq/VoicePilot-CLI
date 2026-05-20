.PHONY: help install dev install-all test test-cov lint typecheck format clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	pip install -e .

dev: ## Install with development dependencies
	pip install -e ".[dev]"

install-all: ## Install with all optional dependencies
	pip install -e ".[all,dev]"

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=voicepilot_cli --cov-report=html --cov-report=term-missing

lint: ## Lint code with ruff
	ruff check voicepilot_cli/

typecheck: ## Type check with mypy
	mypy voicepilot_cli/

format: ## Format code with ruff
	ruff format voicepilot_cli/
	ruff check --fix voicepilot_cli/

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

run: ## Run voicepilot in chat mode
	python -m voicepilot_cli chat

run-voice: ## Run voicepilot in voice mode
	python -m voicepilot_cli chat --mode voice
