"""A maintenance interval repeats; it is not a milestone the odometer passes once."""

from service_advisor_api.recommendations import evaluate_maintenance
from service_advisor_api.service_history import ServiceRecord

COROLLA = {"make": "Toyota", "model": "Corolla", "engine": "2.0L", "drivetrain": "FWD", "market": "Mexico"}
RANGER = {"make": "Ford", "model": "Ranger", "engine": "2.3L", "drivetrain": "4WD", "market": "Mexico"}


def _serviced_at(odometer_km: int) -> tuple[ServiceRecord, ...]:
    return (ServiceRecord("service-1", "TOYOTA-10K", "completed", odometer_km=odometer_km),)


def test_a_serviced_vehicle_is_measured_from_its_last_service() -> None:
    """What if the odometer is high but the service was done recently?"""
    recommendation = evaluate_maintenance(
        37_800, "2026-08-01", **COROLLA, completed_services=_serviced_at(32_000)
    )

    assert recommendation.state == "completed"
    assert "5,800 km" in recommendation.due_reason


def test_the_next_cycle_comes_due_again() -> None:
    """What if the vehicle drives another full interval after being serviced?"""
    recommendation = evaluate_maintenance(
        48_100, "2026-08-01", **COROLLA, completed_services=_serviced_at(32_000)
    )

    assert recommendation.state == "due_now"
    assert recommendation.actionable is True


def test_a_long_neglected_vehicle_is_overdue_from_its_last_service() -> None:
    recommendation = evaluate_maintenance(
        60_000, "2026-08-01", **COROLLA, completed_services=_serviced_at(32_000)
    )

    assert recommendation.state == "overdue"


def test_a_vehicle_with_no_history_is_measured_from_zero() -> None:
    """What if nothing was ever recorded — the odometer is all the evidence there is."""
    recommendation = evaluate_maintenance(37_800, "2026-08-01", **COROLLA)

    assert recommendation.state == "overdue"


def test_the_most_recent_service_is_the_one_that_counts() -> None:
    history = (
        ServiceRecord("older", "TOYOTA-10K", "completed", odometer_km=16_000),
        ServiceRecord("newer", "TOYOTA-10K", "completed", odometer_km=32_000),
    )

    recommendation = evaluate_maintenance(
        37_800, "2026-08-01", **COROLLA, completed_services=history
    )

    assert recommendation.state == "completed"


def test_a_service_for_another_code_does_not_reset_this_cycle() -> None:
    """What if the shop did a different job — that is not this interval."""
    history = (ServiceRecord("other", "TOYOTA-30K", "completed", odometer_km=32_000),)

    recommendation = evaluate_maintenance(
        37_800, "2026-08-01", **COROLLA, completed_services=history
    )

    assert recommendation.state == "overdue"


def test_a_range_interval_also_repeats() -> None:
    history = (ServiceRecord("service-1", "FORD-SCHED-E", "completed", odometer_km=12_000),)

    recommendation = evaluate_maintenance(
        24_500, "2026-08-01", **RANGER, completed_services=history
    )

    assert recommendation.state == "due_now"


def test_every_seeded_vehicle_lands_in_a_believable_state() -> None:
    """The fleet should show a spread, not ten identical verdicts."""
    from fastapi.testclient import TestClient

    from service_advisor_api.main import app
    from service_advisor_api.state import service_history_store, vehicle_store

    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    states = []
    for vehicle_id in (row[1] for row in vehicle_store.SEED_ROWS):
        vehicle = client.get(f"/vehicles/{vehicle_id}", headers=headers).json()
        client.post(
            f"/vehicles/{vehicle_id}/check-ins",
            headers=headers,
            json={
                "current_mileage_km": vehicle["prior_mileage_km"],
                "checked_in_on": "2026-08-01",
                "use_profile": "normal",
                "severe_use_factors": [],
                "concern": "Revision",
                "appointment_window": "Manana",
                "message_consent": True,
            },
        )
        states.append(client.get(f"/vehicles/{vehicle_id}/recommendation", headers=headers).json()["state"])

    assert service_history_store.completed("demo-shop", "toyota-corolla-2022-le")
    assert len(set(states)) >= 3, states
    assert states.count("overdue") <= 3, states


def test_an_odometer_below_the_last_service_does_not_go_negative() -> None:
    """What if the recorded odometer is lower than the last service — bad data, not a cycle."""
    recommendation = evaluate_maintenance(
        20_000, "2026-08-01", **COROLLA, completed_services=_serviced_at(32_000)
    )

    assert recommendation.state == "completed"
    assert "-" not in recommendation.due_reason
