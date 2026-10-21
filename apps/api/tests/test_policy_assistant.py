from datetime import timedelta

import pytest
from helpers import count, session_of

from movon_hr.core.time import jakarta_date
from movon_hr.modules.policies.models import PolicyAnswerAudit

pytestmark = pytest.mark.anyio


async def create_policy(client, headers: dict[str, str], *, state: str = "published") -> dict:
    response = await client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "title": "Sick Leave Policy",
            "category": "leave",
            "language": "en",
            "effective_date": str(jakarta_date() - timedelta(days=1)),
            "sections": [
                {
                    "id": "medical-certificate",
                    "heading": "Medical certificate",
                    "body": "A doctor letter is required after two sick days.",
                }
            ],
        },
    )
    assert response.status_code == 200
    policy = response.json()
    if state == "published":
        assert (
            await client.post(f"/api/v1/policies/{policy['id']}/publish", headers=headers)
        ).status_code == 200
    return policy


async def test_hr_publishes_policy_and_employee_gets_grounded_citation(
    client, db, login_headers
) -> None:
    hr = await login_headers("hr@movon.test")
    policy = await create_policy(client, hr)
    response = await client.post(
        "/api/v1/policy-assistant/questions",
        headers=await login_headers("employee@movon.test"),
        json={"question": "Do I need a doctor letter for sick leave?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "supported"
    assert body["citations"] == [{**body["citations"][0]}]
    assert body["citations"][0]["policy_id"] == policy["id"]
    assert body["citations"][0]["section_id"] == policy["sections"][0]["id"]
    assert await count(db, PolicyAnswerAudit)


async def test_draft_and_cross_tenant_policy_never_answer_question(client, login_headers) -> None:
    hr = await login_headers("hr@movon.test")
    await create_policy(client, hr, state="draft")
    response = await client.post(
        "/api/v1/policy-assistant/questions",
        headers=await login_headers("employee@movon.test"),
        json={"question": "Do I need a doctor letter for sick leave?"},
    )
    assert response.json()["confidence"] == "insufficient_evidence"

    other = await client.post(
        "/api/v1/auth/signup",
        json={
            "company_name": "Tenant Two",
            "admin_name": "Admin Dua",
            "email": "hr@two.test",
            "password": "Company123",
        },
    )
    await create_policy(client, session_of(other))
    assert (
        await client.post(
            "/api/v1/policy-assistant/questions",
            headers=await login_headers("employee@movon.test"),
            json={"question": "doctor letter"},
        )
    ).json()["confidence"] == "insufficient_evidence"


async def test_non_hr_cannot_manage_policies_and_empty_evidence_is_safe(
    client, login_headers
) -> None:
    employee = await login_headers("employee@movon.test")
    assert (await client.get("/api/v1/policies", headers=employee)).status_code == 403
    assert (await client.post("/api/v1/policies", headers=employee, json={})).status_code in {
        403,
        422,
    }
    response = await client.post(
        "/api/v1/policy-assistant/questions",
        headers=employee,
        json={"question": "What is my salary?"},
    )
    assert response.status_code == 200
    assert response.json()["confidence"] == "insufficient_evidence"
    assert response.json()["citations"] == []
