import pytest
from fastapi.testclient import TestClient

from service_advisor_api.knowledge import EvidenceUnavailableError, KnowledgePack
from service_advisor_api.main import app
from service_advisor_api.recommendations import evaluate_maintenance

HONDA_CONFIGURATIONS = {
    "honda-civic-2019-lx": {
        "make": "Honda", "model": "Civic", "engine": "2.0L", "drivetrain": "FWD",
        "market": "Mexico", "service_code": "HONDA-A1", "page": 42, "interval": 48_000,
        "version": "honda-civic-2019-lx-v1",
    },
    "honda-crv-2021-ex": {
        "make": "Honda", "model": "CR-V", "engine": "1.5T", "drivetrain": "AWD",
        "market": "Mexico", "service_code": "HONDA-B1", "page": 55, "interval": 40_000,
        "version": "honda-crv-2021-ex-v1",
    },
    "honda-accord-2020-sport": {
        "make": "Honda", "model": "Accord", "engine": "1.5T", "drivetrain": "FWD",
        "market": "Mexico", "service_code": "HONDA-A2", "page": 61, "interval": 32_000,
        "version": "honda-accord-2020-sport-v1",
    },
}


def _advisor_headers(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


@pytest.mark.parametrize("vehicle_id", sorted(HONDA_CONFIGURATIONS), ids=sorted(HONDA_CONFIGURATIONS))
def test_each_configuration_has_market_labeled_reviewed_evidence(vehicle_id: str) -> None:
    expected = HONDA_CONFIGURATIONS[vehicle_id]

    source, rule = KnowledgePack().rule_for(
        make=expected["make"],
        model=expected["model"],
        engine=expected["engine"],
        drivetrain=expected["drivetrain"],
        market=expected["market"],
    )

    assert source.market == "Mexico"
    assert source.review_state == "reviewed"
    assert source.checksum
    assert source.fallback_market is False
    assert (rule.service_code, rule.version, rule.citation_page) == (
        expected["service_code"],
        expected["version"],
        expected["page"],
    )
    assert rule.immutable is True


@pytest.mark.parametrize("vehicle_id", sorted(HONDA_CONFIGURATIONS), ids=sorted(HONDA_CONFIGURATIONS))
def test_advisor_completes_a_check_in_and_grounded_recommendation(vehicle_id: str) -> None:
    expected = HONDA_CONFIGURATIONS[vehicle_id]
    client = TestClient(app)
    headers = _advisor_headers(client)
    vehicle = client.get(f"/vehicles/{vehicle_id}", headers=headers).json()
    client.post(
        f"/vehicles/{vehicle_id}/check-ins",
        headers=headers,
        json={
            "current_mileage_km": expected["interval"],
            "checked_in_on": "2026-07-30",
            "use_profile": "normal",
            "severe_use_factors": [],
            "concern": "Servicio programado",
            "appointment_window": "Manana",
            "message_consent": True,
        },
    )

    recommendation = client.get(f"/vehicles/{vehicle_id}/recommendation", headers=headers).json()

    assert vehicle["drivetrain"] == expected["drivetrain"]
    assert recommendation["state"] in ("due_now", "completed", "declined")
    assert recommendation["service_code"] == expected["service_code"]
    assert recommendation["rule_version"] == expected["version"]
    assert recommendation["citation_page"] == expected["page"]


@pytest.mark.parametrize("vehicle_id", sorted(HONDA_CONFIGURATIONS), ids=sorted(HONDA_CONFIGURATIONS))
def test_each_configuration_reports_insufficient_evidence_when_it_is_withheld(
    vehicle_id: str,
) -> None:
    expected = HONDA_CONFIGURATIONS[vehicle_id]

    recommendation = evaluate_maintenance(
        expected["interval"],
        "2026-07-30",
        make=expected["make"],
        model=expected["model"],
        engine=expected["engine"],
        drivetrain=expected["drivetrain"],
        market=expected["market"],
        evidence_available=False,
    )

    assert recommendation.actionable is False
    assert recommendation.confidence == "insufficient"
    assert recommendation.citation_page is None


def test_cross_model_evidence_is_never_retrieved_silently() -> None:
    with pytest.raises(EvidenceUnavailableError):
        KnowledgePack().rule_for(
            make="Honda", model="Fit", engine="1.5L", drivetrain="FWD", market="Mexico"
        )


def test_cross_market_evidence_is_never_retrieved_silently() -> None:
    with pytest.raises(EvidenceUnavailableError):
        KnowledgePack().rule_for(
            make="Honda", model="Civic", engine="2.0L", drivetrain="FWD", market="United States"
        )


def test_cross_engine_evidence_is_never_retrieved_silently() -> None:
    recommendation = evaluate_maintenance(
        48_000,
        "2026-07-30",
        make="Honda",
        model="Civic",
        engine="1.5T",
        drivetrain="FWD",
        market="Mexico",
    )

    assert recommendation.actionable is False
    assert recommendation.warnings == (
        "No reviewed rule covers Honda Civic 1.5T FWD in Mexico",
    )


def test_each_configuration_keeps_its_own_interval() -> None:
    civic = evaluate_maintenance(40_000, "2026-07-30", **_config("honda-civic-2019-lx"))
    crv = evaluate_maintenance(40_000, "2026-07-30", **_config("honda-crv-2021-ex"))

    assert civic.state == "informational"
    assert crv.state == "due_now"


def _config(vehicle_id: str) -> dict[str, str]:
    expected = HONDA_CONFIGURATIONS[vehicle_id]
    return {key: expected[key] for key in ("make", "model", "engine", "drivetrain", "market")}
