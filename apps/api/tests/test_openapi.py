from movon_hr.main import app
from movon_hr.openapi import SPEC, render


def test_committed_spec_matches_the_app() -> None:
    # The web client is generated from this file; a stale copy hides API changes from it.
    assert SPEC.read_text(encoding="utf-8") == render(), (
        "openapi.json is stale: run `uv run python -m movon_hr.openapi` in apps/api"
    )


def test_operation_ids_are_unique() -> None:
    # Ids are handler names (main.py); FastAPI only warns on a duplicate, and the web client
    # would then export two functions with the same name.
    ids = [op["operationId"] for path in app.openapi()["paths"].values() for op in path.values()]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def test_operation_ids_follow_the_method() -> None:
    # Naming rule in apps/api/AGENTS.md (Kontrak HTTP). GET/PUT/PATCH must use their prefix; a reserved
    # prefix only appears on the method it belongs to (POST actions are free-form).
    allowed = {
        "get": ("list_", "get_"),
        "post": ("create_",),
        "put": ("update_",),
        "patch": ("update_",),
    }
    required = {"get", "put", "patch"}
    reserved = ("list_", "get_", "create_", "update_")
    wrong = [
        f"{method.upper()} {path}: {name}"
        for path, ops in app.openapi()["paths"].items()
        for method, op in ops.items()
        if (name := op["operationId"])
        and (
            (method in required and not name.startswith(allowed[method]))
            or (name.startswith(reserved) and not name.startswith(allowed.get(method, ())))
        )
    ]
    assert not wrong, wrong


def test_response_fields_are_required() -> None:
    # A response always carries every field; an optional one becomes `field?:` in the web
    # client and breaks narrowing on the `result` discriminator.
    schemas = app.openapi()["components"]["schemas"]
    optional = {
        name: sorted(set(schema["properties"]) - set(schema.get("required", [])))
        for name, schema in schemas.items()
        if name.endswith("Out")
        and set(schema.get("properties", {})) - set(schema.get("required", []))
    }
    assert not optional, (
        f"Set json_schema_serialization_defaults_required=True on these models: {optional}"
    )
