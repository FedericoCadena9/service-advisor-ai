"""Toyota pack: reviewed evidence, its shape, and what it refuses to do.

Every configuration is a labeled United States fallback: the research found no public
Mexican schedule binding model, year, engine and drivetrain. The rule answers, and says so.
"""

import pytest
from fastapi.testclient import TestClient

from service_advisor_api.knowledge import (
    FixedInterval,
    KnowledgePack,
)
from service_advisor_api.main import app
from service_advisor_api.recommendations import evaluate_maintenance

CONFIGURATIONS = {'toyota-corolla-2022-le': {'make': 'Toyota',
                            'model': 'Corolla',
                            'engine': '2.0L',
                            'drivetrain': 'FWD',
                            'market': 'Mexico',
                            'service_code': 'TOYOTA-10K',
                            'page': 38,
                            'version': 'toyota-corolla-2022-le-us-v1',
                            'mileage': 16093,
                            'state': 'due_now'},
 'toyota-rav4-2021-xle': {'make': 'Toyota',
                          'model': 'RAV4',
                          'engine': '2.5L',
                          'drivetrain': 'AWD',
                          'market': 'Mexico',
                          'service_code': 'TOYOTA-20K',
                          'page': 38,
                          'version': 'toyota-rav4-2021-xle-us-v1',
                          'mileage': 16093,
                          'state': 'due_now'},
 'toyota-tacoma-2020-sr5': {'make': 'Toyota',
                            'model': 'Tacoma',
                            'engine': '3.5L',
                            'drivetrain': '4WD',
                            'market': 'Mexico',
                            'service_code': 'TOYOTA-30K',
                            'page': 35,
                            'version': 'toyota-tacoma-2020-sr5-us-v1',
                            'mileage': 12070,
                            'state': 'due_now'}}


def _config(vehicle_id: str) -> dict[str, str]:
    expected = CONFIGURATIONS[vehicle_id]
    return {key: expected[key] for key in ("make", "model", "engine", "drivetrain", "market")}


def _advisor_headers(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


@pytest.mark.parametrize("vehicle_id", sorted(CONFIGURATIONS), ids=sorted(CONFIGURATIONS))
def test_each_configuration_names_the_document_that_was_read(vehicle_id: str) -> None:
    expected = CONFIGURATIONS[vehicle_id]

    source, rule = KnowledgePack().rule_for(**_config(vehicle_id), allow_fallback_market=True)

    assert source.review_state == "reviewed"
    assert source.market == "United States"
    assert source.fallback_market is True
    assert source.source_url.startswith("https://")
    assert source.retrieval_date == "2026-07-31"
    assert (rule.service_code, rule.version, rule.citation_page) == (
        expected["service_code"],
        expected["version"],
        expected["page"],
    )
    assert rule.immutable is True


@pytest.mark.parametrize("vehicle_id", sorted(CONFIGURATIONS), ids=sorted(CONFIGURATIONS))
def test_each_rule_uses_the_shape_its_manual_publishes(vehicle_id: str) -> None:
    _, rule = KnowledgePack().rule_for(**_config(vehicle_id), allow_fallback_market=True)

    assert isinstance(rule.interval, FixedInterval)


@pytest.mark.parametrize("vehicle_id", sorted(CONFIGURATIONS), ids=sorted(CONFIGURATIONS))
def test_the_advisor_gets_a_labeled_recommendation(vehicle_id: str) -> None:
    """The state comes from the rule's own shape, not from a number pinned in this test."""
    expected = CONFIGURATIONS[vehicle_id]
    client = TestClient(app)
    headers = _advisor_headers(client)
    vehicle = client.get(f"/vehicles/{vehicle_id}", headers=headers).json()
    mileage = vehicle["prior_mileage_km"]
    _, rule = KnowledgePack().rule_for(**_config(vehicle_id), allow_fallback_market=True)
    client.post(
        f"/vehicles/{vehicle_id}/check-ins",
        headers=headers,
        json={
            "current_mileage_km": mileage,
            "checked_in_on": "2026-08-01",
            "use_profile": "normal",
            "severe_use_factors": [],
            "concern": "Servicio programado",
            "appointment_window": "Manana",
            "message_consent": True,
        },
    )

    recommendation = client.get(f"/vehicles/{vehicle_id}/recommendation", headers=headers).json()

    assert recommendation["warnings"] == [
        "Evidence comes from the labeled United States fallback market"
    ]
    if recommendation["state"] not in ("completed", "declined"):
        assert recommendation["state"] == rule.due_state(mileage)[0]
    if recommendation["actionable"]:
        assert recommendation["citation_page"] == expected["page"]
        assert recommendation["rule_version"] == expected["version"]


@pytest.mark.parametrize("vehicle_id", sorted(CONFIGURATIONS), ids=sorted(CONFIGURATIONS))
def test_withheld_evidence_leaves_nothing_actionable(vehicle_id: str) -> None:
    recommendation = evaluate_maintenance(
        CONFIGURATIONS[vehicle_id]["mileage"],
        "2026-08-01",
        **_config(vehicle_id),
        evidence_available=False,
    )

    assert recommendation.actionable is False
    assert recommendation.citation_page is None


def test_a_domestic_document_is_still_required_when_asked_for_one() -> None:
    """Refusing the fallback stays possible for a caller that will not accept it."""
    from service_advisor_api.knowledge import FallbackMarketEvidenceError

    with pytest.raises(FallbackMarketEvidenceError):
        KnowledgePack().rule_for(**_config("toyota-corolla-2022-le"))


def test_toyota_rules_are_not_reused_across_models() -> None:
    corolla = evaluate_maintenance(16_093, "2026-08-01", **_config("toyota-corolla-2022-le"))
    tacoma = evaluate_maintenance(16_093, "2026-08-01", **_config("toyota-tacoma-2020-sr5"))

    assert corolla.service_code == "TOYOTA-10K"
    assert tacoma.service_code == "TOYOTA-30K"
    assert corolla.state == "due_now"
    assert tacoma.state == "overdue"

