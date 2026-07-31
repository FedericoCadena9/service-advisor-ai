import pytest
from fastapi.testclient import TestClient

from service_advisor_api.knowledge import EvidenceUnavailableError, KnowledgePack
from service_advisor_api.main import app
from service_advisor_api.recommendations import evaluate_maintenance

FORD_CONFIGURATIONS = {
    "ford-f150-2021-xlt": {
        "make": "Ford", "model": "F-150", "engine": "3.5L", "drivetrain": "4WD",
        "market": "Mexico", "service_code": "FORD-SCHED-A", "page": 27, "interval": 16_000,
        "version": "ford-f150-2021-xlt-35-4wd-v1",
    },
    "ford-escape-2022-se": {
        "make": "Ford", "model": "Escape", "engine": "1.5L", "drivetrain": "FWD",
        "market": "Mexico", "service_code": "FORD-SCHED-C", "page": 33, "interval": 16_000,
        "version": "ford-escape-2022-se-v1",
    },
    "ford-explorer-2020-xlt": {
        "make": "Ford", "model": "Explorer", "engine": "2.3L", "drivetrain": "AWD",
        "market": "Mexico", "service_code": "FORD-SCHED-D", "page": 39, "interval": 24_000,
        "version": "ford-explorer-2020-xlt-v1",
    },
    "ford-ranger-2021-xlt": {
        "make": "Ford", "model": "Ranger", "engine": "2.3L", "drivetrain": "4WD",
        "market": "Mexico", "service_code": "FORD-SCHED-E", "page": 44, "interval": 16_000,
        "version": "ford-ranger-2021-xlt-v1",
    },
}


def _config(vehicle_id: str) -> dict[str, str]:
    expected = FORD_CONFIGURATIONS[vehicle_id]
    return {key: expected[key] for key in ("make", "model", "engine", "drivetrain", "market")}


def _advisor_headers(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


@pytest.mark.parametrize("vehicle_id", sorted(FORD_CONFIGURATIONS), ids=sorted(FORD_CONFIGURATIONS))
def test_each_configuration_has_market_labeled_reviewed_evidence(vehicle_id: str) -> None:
    expected = FORD_CONFIGURATIONS[vehicle_id]

    source, rule = KnowledgePack().rule_for(**_config(vehicle_id))

    assert (source.market, source.review_state, source.fallback_market) == (
        "Mexico",
        "reviewed",
        False,
    )
    assert (rule.service_code, rule.version, rule.citation_page) == (
        expected["service_code"],
        expected["version"],
        expected["page"],
    )
    assert rule.immutable is True


@pytest.mark.parametrize("vehicle_id", sorted(FORD_CONFIGURATIONS), ids=sorted(FORD_CONFIGURATIONS))
def test_advisor_completes_a_check_in_and_grounded_recommendation(vehicle_id: str) -> None:
    expected = FORD_CONFIGURATIONS[vehicle_id]
    client = TestClient(app)
    headers = _advisor_headers(client)
    vehicle = client.get(f"/vehicles/{vehicle_id}", headers=headers).json()
    client.post(
        f"/vehicles/{vehicle_id}/check-ins",
        headers=headers,
        json={
            "current_mileage_km": expected["interval"],
            "checked_in_on": "2026-07-31",
            "use_profile": "normal",
            "severe_use_factors": [],
            "concern": "Servicio programado",
            "appointment_window": "Manana",
            "message_consent": True,
        },
    )

    recommendation = client.get(f"/vehicles/{vehicle_id}/recommendation", headers=headers).json()

    assert (vehicle["engine"], vehicle["drivetrain"]) == (
        expected["engine"],
        expected["drivetrain"],
    )
    assert recommendation["state"] == "due_now"
    assert recommendation["service_code"] == expected["service_code"]
    assert recommendation["rule_version"] == expected["version"]
    assert recommendation["citation_page"] == expected["page"]


def test_engine_metadata_selects_the_matching_f150_schedule() -> None:
    _, four_wheel = KnowledgePack().rule_for(
        make="Ford", model="F-150", engine="3.5L", drivetrain="4WD", market="Mexico"
    )
    _, rear_wheel = KnowledgePack().rule_for(
        make="Ford", model="F-150", engine="5.0L", drivetrain="RWD", market="Mexico"
    )

    assert four_wheel.service_code == "FORD-SCHED-A"
    assert rear_wheel.service_code == "FORD-SCHED-B"
    assert four_wheel.interval_km != rear_wheel.interval_km


def test_incompatible_engine_is_never_retrieved() -> None:
    with pytest.raises(EvidenceUnavailableError):
        KnowledgePack().rule_for(
            make="Ford", model="F-150", engine="2.7L", drivetrain="4WD", market="Mexico"
        )


def test_incompatible_drivetrain_is_never_retrieved() -> None:
    with pytest.raises(EvidenceUnavailableError):
        KnowledgePack().rule_for(
            make="Ford", model="Ranger", engine="2.3L", drivetrain="AWD", market="Mexico"
        )


def test_incompatible_powertrain_is_reported_as_insufficient_evidence() -> None:
    recommendation = evaluate_maintenance(
        16_000,
        "2026-07-31",
        make="Ford",
        model="F-150",
        engine="5.0L",
        drivetrain="4WD",
        market="Mexico",
    )

    assert recommendation.actionable is False
    assert recommendation.confidence == "insufficient"
    assert recommendation.warnings == ("No reviewed rule covers Ford F-150 5.0L 4WD in Mexico",)


@pytest.mark.parametrize("vehicle_id", sorted(FORD_CONFIGURATIONS), ids=sorted(FORD_CONFIGURATIONS))
def test_each_configuration_reports_insufficient_evidence_when_it_is_withheld(
    vehicle_id: str,
) -> None:
    recommendation = evaluate_maintenance(
        FORD_CONFIGURATIONS[vehicle_id]["interval"],
        "2026-07-31",
        **_config(vehicle_id),
        evidence_available=False,
    )

    assert recommendation.actionable is False
    assert recommendation.citation_page is None
