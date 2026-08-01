"""Ford pack: reviewed evidence, its shape, and what it refuses to do.

Every configuration is a labeled United States fallback: the research found no public
Mexican schedule binding model, year, engine and drivetrain. The rule answers, and says so.
"""

import pytest
from fastapi.testclient import TestClient

from service_advisor_api.knowledge import (
    KnowledgePack,
    RangeInterval,
)
from service_advisor_api.main import app
from service_advisor_api.recommendations import evaluate_maintenance

CONFIGURATIONS = {'ford-f150-2021-xlt': {'make': 'Ford',
                        'model': 'F-150',
                        'engine': '3.5L',
                        'drivetrain': '4WD',
                        'market': 'Mexico',
                        'service_code': 'FORD-SCHED-A',
                        'page': 667,
                        'version': 'ford-f150-2021-xlt-35-4wd-us-v1',
                        'mileage': 12000,
                        'state': 'due_now'},
 'ford-escape-2022-se': {'make': 'Ford',
                         'model': 'Escape',
                         'engine': '1.5L',
                         'drivetrain': 'FWD',
                         'market': 'Mexico',
                         'service_code': 'FORD-SCHED-C',
                         'page': 485,
                         'version': 'ford-escape-2022-se-us-v1',
                         'mileage': 12000,
                         'state': 'due_now'},
 'ford-explorer-2020-xlt': {'make': 'Ford',
                            'model': 'Explorer',
                            'engine': '2.3L',
                            'drivetrain': 'AWD',
                            'market': 'Mexico',
                            'service_code': 'FORD-SCHED-D',
                            'page': 491,
                            'version': 'ford-explorer-2020-xlt-us-v1',
                            'mileage': 12070,
                            'state': 'due_now'},
 'ford-ranger-2021-xlt': {'make': 'Ford',
                          'model': 'Ranger',
                          'engine': '2.3L',
                          'drivetrain': '4WD',
                          'market': 'Mexico',
                          'service_code': 'FORD-SCHED-E',
                          'page': 419,
                          'version': 'ford-ranger-2021-xlt-us-v1',
                          'mileage': 12000,
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

    assert isinstance(rule.interval, RangeInterval)


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


def test_engine_and_drivetrain_select_the_f150_schedule() -> None:
    _, four_wheel = KnowledgePack().rule_for(
        make="Ford", model="F-150", engine="3.5L", drivetrain="4WD", market="Mexico",
        allow_fallback_market=True,
    )
    _, rear_wheel = KnowledgePack().rule_for(
        make="Ford", model="F-150", engine="5.0L", drivetrain="RWD", market="Mexico",
        allow_fallback_market=True,
    )

    assert four_wheel.service_code == "FORD-SCHED-A"
    assert rear_wheel.service_code == "FORD-SCHED-B"


def test_an_incompatible_powertrain_reports_insufficient_evidence() -> None:
    recommendation = evaluate_maintenance(
        16_000, "2026-08-01", make="Ford", model="F-150", engine="5.0L",
        drivetrain="4WD", market="Mexico",
    )

    assert recommendation.actionable is False
    assert recommendation.warnings == ("No reviewed rule covers Ford F-150 5.0L 4WD in Mexico",)


def test_a_range_is_due_anywhere_inside_its_span() -> None:
    """Ford publishes 12,000-16,000 km, so both ends are due, not just one number."""
    early = evaluate_maintenance(12_000, "2026-08-01", **_config("ford-ranger-2021-xlt"))
    late = evaluate_maintenance(16_000, "2026-08-01", **_config("ford-ranger-2021-xlt"))

    assert early.state == "due_now"
    assert late.state == "due_now"

