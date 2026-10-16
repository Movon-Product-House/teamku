"""U11: policy section ids (plan Schema Changes note 3)."""

import uuid
from datetime import date

import pytest
from helpers import count

from movon_hr.modules.policies.models import PolicySection

pytestmark = pytest.mark.anyio


def body(*sections: dict) -> dict:
    return {"title": "Leave Policy", "effective_date": str(date(2026, 1, 1)), "sections": sections}


async def test_section_id_is_kept_only_when_it_names_an_existing_section(
    client, db, login_headers
) -> None:
    hr = await login_headers("hr@movon.test")
    created = await client.post(
        "/api/v1/policies",
        headers=hr,
        json=body(
            {"id": "client-id", "heading": "A", "body": "First"},
            {"heading": "B", "body": "Second"},
        ),
    )
    assert created.status_code == 200
    first, second = created.json()["sections"]
    uuid.UUID(first["id"])  # a client-sent id that is not an existing section is replaced
    other = await client.post(
        "/api/v1/policies", headers=hr, json=body({"heading": "X", "body": "Other"})
    )
    foreign_id = other.json()["sections"][0]["id"]

    updated = await client.put(
        f"/api/v1/policies/{created.json()['id']}",
        headers=hr,
        json=body(
            {"id": second["id"], "heading": "B2", "body": "Second, edited"},
            {"id": foreign_id, "heading": "C", "body": "From another policy"},
            {"id": second["id"], "heading": "D", "body": "Same id twice"},
        ),
    )
    assert updated.status_code == 200
    sections = updated.json()["sections"]
    assert [item["position"] for item in sections] == [0, 1, 2]
    assert sections[0]["id"] == second["id"]
    assert sections[0]["heading"] == "B2"
    new_ids = {sections[1]["id"], sections[2]["id"]}
    assert len(new_ids) == 2
    assert new_ids.isdisjoint({first["id"], second["id"], foreign_id})
    # "A" was dropped: 3 sections here plus 1 in the other policy.
    assert await count(db, PolicySection) == 4
