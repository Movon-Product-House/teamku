#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
PYTHONPATH=src uv run lint-imports  # the project is not installed as a package
uv run pytest -q
