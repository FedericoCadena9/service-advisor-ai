from fastapi.testclient import TestClient

from service_advisor_api.main import app


def test_advisor_run_is_resumable_and_decisions_are_idempotent() -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    run = client.post("/advisor-runs", headers=headers).json()

    resumed = client.get(f"/advisor-runs/{run['id']}", headers=headers)
    approved = client.post(f"/advisor-runs/{run['id']}/decision", json={"decision": "approve"}, headers=headers)
    repeated = client.post(f"/advisor-runs/{run['id']}/decision", json={"decision": "approve"}, headers=headers)

    assert resumed.json()["events"] == ["started", "context_loaded", "awaiting_human_review"]
    assert approved.json() == repeated.json()
    assert approved.json()["command_executed"] is True
