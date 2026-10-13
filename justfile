# iconpilot — deterministic tooling + state for SVG icon packs

default:
    @just --list

# Install/sync all dependencies (dev + docs)
sync:
    uv sync --all-groups

# Run the test suite
test:
    uv run pytest

# Lint (ruff check + format check + ty type check)
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/
    uv run ty check src/

# Auto-format
fmt:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/

# Everything CI runs
check: lint test

# Live-preview the documentation
docs-serve:
    uv run --group docs zensical serve

# Build the documentation (→ site/)
docs-build:
    uv run --group docs zensical build

# Build the Docker image locally
docker-build tag="iconpilot:dev":
    docker build -t {{tag}} .
