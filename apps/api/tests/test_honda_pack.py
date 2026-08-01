"""Honda pack: reviewed evidence, its shape, and what it refuses to do.

Every configuration is a labeled United States fallback: the research found no public
Mexican schedule binding model, year, engine and drivetrain. The rule answers, and says so.
"""

import pytest
from fastapi.testclient import TestClient

from service_advisor_api.knowledge import (
    ConditionInterval,
    EvidenceUnavailableError,
    KnowledgePack,
)
from service_advisor_api.main import app
from service_advisor_api.recommendations import evaluate_maintenance

CONFIGURATIONS = {'honda-civic-2019-lx': {'make': 'Honda',
                         'model': 'Civic',
                         'engine': '2.0L',
                         'drivetrain': 'FWD',
                         'market': 'Mexico',
                         'service_code': 'HONDA-A1',
                         'page': 1,
                         'version': 'honda-civic-2019-lx-us-v1',
                         'mileage': 48000,
                         'state': 'completed'},
 'honda-crv-2021-ex': {'make': 'Honda',
                       'model': 'CR-V',
                       'engine': '1.5T',
                       'drivetrain': 'AWD',
                       'market': 'Mexico',
                       'service_code': 'HONDA-B1',
                       'page': 1,
                       'version': 'honda-crv-2021-ex-us-v1',
                       'mileage': 40000,
                       'state': 'informational'},
 'honda-accord-2020-sport': {'make': 'Honda',
                             'model': 'Accord',
                             'engine': '1.5T',
                             'drivetrain': 'FWD',
                             'market': 'Mexico',
                             'service_code': 'HONDA-A2',
                             'page': 1,
                             'version': 'honda-accord-2020-sport-us-v1',
                             'mileage': 32000,
                             'state': 'informational'}}


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

    assert isinstance(rule.interval, ConditionInterval)


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


def test_cross_model_evidence_is_never_retrieved_silently() -> None:
    with pytest.raises(EvidenceUnavailableError):
        KnowledgePack().rule_for(
            make="Honda", model="Fit", engine="1.5L", drivetrain="FWD", market="Mexico"
        )


def test_a_condition_based_rule_refuses_to_read_the_odometer() -> None:
    """Honda publishes no distance for these services; the Maintenance Minder decides."""
    recommendation = evaluate_maintenance(
        200_000, "2026-08-01", **_config("honda-civic-2019-lx")
    )

    assert recommendation.state == "informational"
    assert "Maintenance Minder" in recommendation.due_reason

