"""The committed OpenAPI spec the web client is generated from.

Refresh after any API change: ``uv run python -m movon_hr.openapi`` (writes ``openapi.json``).
"""

import json
from pathlib import Path

from movon_hr.main import app

SPEC = Path(__file__).resolve().parents[2] / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    SPEC.write_text(render(), encoding="utf-8")
