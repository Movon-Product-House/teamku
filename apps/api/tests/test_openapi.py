from movon_hr.openapi import SPEC, render


def test_committed_spec_matches_the_app() -> None:
    # The web client is generated from this file; a stale copy hides API changes from it.
    assert SPEC.read_text(encoding="utf-8") == render(), (
        "openapi.json is stale: run `uv run python -m movon_hr.openapi` in apps/api"
    )
