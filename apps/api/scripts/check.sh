#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run lint-imports
uv run pytest -q
