"""Record tests/contract/shapes.json from the OLD in-memory API (plan U0).

Run from apps/api: ``uv run python tests/contract/record_shapes.py``.
shapes.json is frozen after U0; this script is deleted with the old code in U12.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import httpx
from shape_capture import SHAPES_PATH, capture, uncovered_routes

from movon_hr.main import app
from movon_hr.modules.api import reset_demo_store


async def main() -> None:
    logging.disable(logging.INFO)  # console mailer logs every email body
    reset_demo_store()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        shapes = await capture(client)
    missing = uncovered_routes(app, shapes)
    if missing:
        sys.exit("Routes with no recorded success response:\n  " + "\n  ".join(missing))
    SHAPES_PATH.write_text(json.dumps(shapes, indent=2, sort_keys=True) + "\n")
    routes = {key.split(" | ")[0] for key in shapes}
    print(f"Wrote {len(shapes)} responses over {len(routes)} routes to {SHAPES_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
