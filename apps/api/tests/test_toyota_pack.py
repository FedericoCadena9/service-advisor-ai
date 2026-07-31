import pytest
from fastapi.testclient import TestClient

from service_advisor_api.knowledge import FallbackMarketEvidenceError, KnowledgePack
from service_advisor_api.main import app
from service_advisor_api.recommendations import evaluate_maintenance

TOYOTA_CONFIGURATIONS = {
    "toyota-corolla-2022-le": {
        "make": "Toyota", "model": "Corolla", "engine": "2.0L", "drivetrain": "FWD",
        "market": "Mexico", "service_code": "TOYOTA-10K", "page": 18, "interval": 40_000,
        "version": "toyota-corolla-2022-le-v1", "fallback": False,
    },
    "toyota-rav4-2021-xle": {
        "make": "Toyota", "model": "RAV4", "engine": "2.5L", "drivetrain": "AWD",
        "market": "Mexico", "service_code": "TOYOTA-20K", "page": 24, "interval": 48_000,
        "version": "toyota-rav4-2021-xle-v1", "fallback": False,
    },
    "toyota-tacoma-2020-sr5": {
        "make": "Toyota", "model": "Tacoma", "engine": "3.5L", "drivetrain": "4WD",
        "market": "Mexico", "service_code": "TOYOTA-30K", "page": 31, "interval": 48_000,
        "version": "toyota-tacoma-2020-sr5-us-v1", "fallback": True,
    },
}


def _config(vehicle_id: str) -> dict[str, str]:
    expected = TOYOTA_CONFIGURATIONS[vehicle_id]
    return {key: expected[key] for key in ("make", "model", "engine", "drivetrain", "market")}


def _advisor_headers(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def _check_in(client: TestClient, headers: dict[str, str], vehicle_id: str, mileage: int) -> None:
    client.post(
        f"/vehicles/{vehicle_id}/check-ins",
        headers=headers,
        json={
            "current_mileage_km": mileage,
            "checked_in_on": "2026-07-30",
            "use_profile": "normal",
            "severe_use_factors": [],
            "concern": "Servicio programado",
            "appointment_window": "Manana",
            "message_consent": True,
        },
    )


@pytest.mark.parametrize("vehicle_id", sorted(TOYOTA_CONFIGURATIONS), ids=sorted(TOYOTA_CONFIGURATIONS))
def test_each_configuration_has_market_labeled_reviewed_evidence(vehicle_id: str) -> None:
    expected = TOYOTA_CONFIGURATIONS[vehicle_id]

    source, rule = KnowledgePack().rule_for(**_config(vehicle_id), allow_fallback_market=True)

    assert source.review_state == "reviewed"
    assert source.fallback_market is expected["fallback"]
    assert source.market == ("United States" if expected["fallback"] else "Mexico")
    assert (rule.service_code, rule.version, rule.citation_page) == (
        expected["service_code"],
        expected["version"],
        expected["page"],
    )


@pytest.mark.parametrize("vehicle_id", sorted(TOYOTA_CONFIGURATIONS), ids=sorted(TOYOTA_CONFIGURATIONS))
def test_advisor_completes_a_check_in_and_grounded_recommendation(vehicle_id: str) -> None:
    expected = TOYOTA_CONFIGURATIONS[vehicle_id]
    client = TestClient(app)
    headers = _advisor_headers(client)
    _check_in(client, headers, vehicle_id, expected["interval"])

    recommendation = client.get(
        f"/vehicles/{vehicle_id}/recommendation",
        headers=headers,
        params={"allow_fallback_market": expected["fallback"]},
    ).json()

    assert recommendation["state"] == "due_now"
    assert recommendation["service_code"] == expected["service_code"]
    assert recommendation["rule_version"] == expected["version"]
    assert recommendation["citation_page"] == expected["page"]


def test_fallback_market_evidence_is_never_combined_silently() -> None:
    with pytest.raises(FallbackMarketEvidenceError):
        KnowledgePack().rule_for(**_config("toyota-tacoma-2020-sr5"))


def test_fallback_market_recommendation_is_refused_until_it_is_reviewed() -> None:
    client = TestClient(app)
    headers = _advisor_headers(client)
    _check_in(client, headers, "toyota-tacoma-2020-sr5", 48_000)

    recommendation = client.get(
        "/vehicles/toyota-tacoma-2020-sr5/recommendation", headers=headers
    ).json()

    assert recommendation["actionable"] is False
    assert recommendation["confidence"] == "insufficient"
    assert recommendation["warnings"] == [
        (
            "Only a United States fallback document exists; it is not combined with "
            "Mexico evidence without explicit review"
        )
    ]


def test_accepted_fallback_evidence_stays_labeled() -> None:
    recommendation = evaluate_maintenance(
        48_000, "2026-07-30", **_config("toyota-tacoma-2020-sr5"), allow_fallback_market=True
    )

    assert recommendation.actionable is True
    assert recommendation.warnings == (
        "Evidence comes from the labeled United States fallback market",
    )


@pytest.mark.parametrize("vehicle_id", sorted(TOYOTA_CONFIGURATIONS), ids=sorted(TOYOTA_CONFIGURATIONS))
def test_each_configuration_reports_insufficient_evidence_when_it_is_withheld(
    vehicle_id: str,
) -> None:
    recommendation = evaluate_maintenance(
        TOYOTA_CONFIGURATIONS[vehicle_id]["interval"],
        "2026-07-30",
        **_config(vehicle_id),
        allow_fallback_market=True,
        evidence_available=False,
    )

    assert recommendation.actionable is False
    assert recommendation.confidence == "insufficient"


def test_toyota_rules_are_not_reused_across_models() -> None:
    corolla = evaluate_maintenance(40_000, "2026-07-30", **_config("toyota-corolla-2022-le"))
    rav4 = evaluate_maintenance(40_000, "2026-07-30", **_config("toyota-rav4-2021-xle"))

    assert corolla.service_code == "TOYOTA-10K"
    assert rav4.state == "informational"
