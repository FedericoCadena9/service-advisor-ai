from fastapi.testclient import TestClient

from service_advisor_api.main import app

CHECKIN = {
    "current_mileage_km": 48_000,
    "checked_in_on": "2026-07-31",
    "use_profile": "normal",
    "severe_use_factors": [],
    "concern": "Rechinido al frenar, contacto +52 55 0000 0000",
    "appointment_window": "Manana",
    "message_consent": True,
}


def _headers(client: TestClient, role: str) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": role})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def _advisor_journey(client: TestClient) -> tuple[dict[str, str], str]:
    headers = _headers(client, "advisor")
    run = client.post("/advisor-runs", headers=headers).json()
    trace_id = run["trace_id"]
    traced = {**headers, "X-Trace-Id": trace_id}
    client.post("/vehicles/honda-civic-2019-lx/check-ins", headers=headers, json=CHECKIN)
    client.get("/vehicles/honda-civic-2019-lx/recommendation", headers=traced)
    client.post(
        "/contextual-chat",
        headers=traced,
        json={"question": "Why", "vehicle_id": "honda-civic-2019-lx", "current_mileage_km": 48_000, "provider_available": True},
    )
    review = client.post(
        "/vehicles/honda-civic-2019-lx/quote-reviews",
        headers=headers,
        json={"service_codes": ["HONDA-A1"]},
    ).json()
    client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=traced,
        json={"decision": "approve", "idempotency_key": "key-1"},
    )
    client.post(f"/advisor-runs/{run['id']}/decision", headers=headers, json={"decision": "approve"})
    return headers, trace_id


def test_advisor_run_emits_correlated_spans_of_every_kind() -> None:
    client = TestClient(app)
    _, trace_id = _advisor_journey(client)

    trace = client.get(f"/admin/traces/{trace_id}", headers=_headers(client, "manager")).json()

    kinds = {span["kind"] for span in trace["spans"]}
    assert kinds == {"http", "workflow", "tool", "retrieval", "provider", "command"}
    assert trace["versions"]["prompt_version"] == "advisor-prompt-v1"
    assert trace["versions"]["dataset_version"] == "canonical-100-v1"
    assert any(span["cost_mxn"] != "0.0000" for span in trace["spans"])
    assert all(span["latency_ms"] > 0 for span in trace["spans"])


def test_exported_traces_contain_no_prohibited_data() -> None:
    client = TestClient(app)
    _, trace_id = _advisor_journey(client)

    trace = client.get(f"/admin/traces/{trace_id}", headers=_headers(client, "manager"))

    assert "Demo Customer" not in trace.text
    assert "+52" not in trace.text
    assert "Rechinido" not in trace.text
    assert "concern" not in trace.text


def test_dashboard_reports_quality_evaluation_and_escalations() -> None:
    client = TestClient(app)
    _advisor_journey(client)

    dashboard = client.get("/admin/dashboard", headers=_headers(client, "manager")).json()

    assert dashboard["trace_count"] >= 1
    assert dashboard["spans_by_kind"]["retrieval"] >= 1
    assert dashboard["citation_rate"] > 0
    assert dashboard["escalation_outcomes"]["approved"] >= 1
    assert dashboard["evaluation_thresholds_met"] is True
    assert dashboard["evaluation_score"] >= 0.95


def test_advisors_cannot_read_traces_or_dashboards() -> None:
    client = TestClient(app)
    headers, trace_id = _advisor_journey(client)

    assert client.get(f"/admin/traces/{trace_id}", headers=headers).status_code == 403
    assert client.get("/admin/dashboard", headers=headers).status_code == 403


def test_traces_from_another_shop_are_not_exported() -> None:
    client = TestClient(app)

    response = client.get("/admin/traces/unknown-trace", headers=_headers(client, "manager"))

    assert response.status_code == 404
