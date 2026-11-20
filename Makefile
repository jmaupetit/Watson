# -- General
SHELL := /bin/bash

# ==============================================================================
# RULES

default: help

# -- Build
bootstrap: ## bootstrap the project for development
bootstrap: \
  build
.PHONY: bootstrap

build: ## install project
	uv sync --locked --all-extras --dev
.PHONY: build

docs-serve: ## run documentation server 
	uv run mkdocs serve -w docs
.PHONY: docs-serve

docs-publish: ## publish documentation
	uv run mkdocs gh-deploy --force
.PHONY: docs-publish

# -- Quality
lint: ## lint all sources
lint: \
  lint-format \
  lint-ruff
.PHONY: lint

lint-format: ## format python sources with ruff format
	@echo 'lint:format started…'
	uv run ruff format watson tests scripts
.PHONY: lint-format

lint-format-check: ## check python sources formatting with ruff format
	@echo 'lint:format check started…'
	uv run ruff format --check watson tests scripts
.PHONY: lint-format-check

lint-ruff: ## lint python sources with ruff
	@echo 'lint:ruff started…'
	uv run ruff check watson tests scripts
.PHONY: lint-ruff

lint-ruff-fix: ## lint and fix python sources with ruff
	@echo 'lint:ruff-fix started…'
	uv run ruff check --fix watson tests scripts
.PHONY: lint-ruff-fix

test: ## run tests
	uv run pytest --cov --cov-report=term-missing --cov-report=html
.PHONY: test

completion-scripts:
	scripts/create-completion-script.sh bash
	scripts/create-completion-script.sh zsh
.PHONY: completion-scripts

# -- Misc
help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
.PHONY: help
