"""Characterization test: every success response keeps the shape frozen in shapes.json (R1)."""

import json

import httpx
import pytest
from shape_capture import ALLOWED_ADDITIONS, SHAPES_PATH, capture, uncovered_routes, without_keys

from movon_hr.main import app


@pytest.mark.anyio
async def test_response_shapes_match_snapshot(client: httpx.AsyncClient) -> None:
    actual = await capture(client)
    expected = json.loads(SHAPES_PATH.read_text())

    assert uncovered_routes(app, actual) == []
    assert sorted(actual) == sorted(expected)
    mismatches = [
        f"{key}\n  expected: {json.dumps(expected[key])}\n  actual:   {json.dumps(shape)}"
        for key, shape in sorted(actual.items())
        if without_keys(shape, ALLOWED_ADDITIONS) != expected[key]
    ]
    assert not mismatches, "Response shapes drifted:\n" + "\n".join(mismatches)
