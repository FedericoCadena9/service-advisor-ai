"""Distance decides only when the manufacturer publishes a distance."""

from service_advisor_api.recommendations import evaluate_maintenance

COROLLA = {"make": "Toyota", "model": "Corolla", "engine": "2.0L", "drivetrain": "FWD", "market": "Mexico"}
CIVIC = {"make": "Honda", "model": "Civic", "engine": "2.0L", "drivetrain": "FWD", "market": "Mexico"}


def test_mileage_boundary_returns_due_now_with_exact_rule_evidence() -> None:
    recommendation = evaluate_maintenance(16_093, "2026-08-01", **COROLLA)

    assert recommendation.state == "due_now"
    assert recommendation.actionable is True
    assert recommendation.service_code == "TOYOTA-10K"
    assert recommendation.rule_version == "toyota-corolla-2022-le-us-v1"
    assert recommendation.citation_page == 38
    assert recommendation.citation_section == "Maintenance Log"


def test_mileage_overdue_and_due_soon_boundaries_are_deterministic() -> None:
    assert evaluate_maintenance(18_094, "2026-08-01", **COROLLA).state == "overdue"
    assert evaluate_maintenance(14_500, "2026-08-01", **COROLLA).state == "due_soon"


def test_a_condition_based_rule_never_becomes_due_by_odometer() -> None:
    """What if the Advisor reads a huge odometer on a Honda instead of a Toyota?"""
    recommendation = evaluate_maintenance(200_000, "2026-08-01", **CIVIC)

    assert recommendation.state == "informational"
    assert recommendation.actionable is False
    assert "Maintenance Minder" in recommendation.due_reason


def test_unsupported_evidence_is_informational_not_actionable() -> None:
    recommendation = evaluate_maintenance(
        16_093, "2026-08-01", **COROLLA, evidence_available=False
    )

    assert recommendation.state == "informational"
    assert recommendation.actionable is False
    assert "Reviewed evidence is unavailable" in recommendation.warnings


def test_every_recommendation_labels_the_market_its_evidence_came_from() -> None:
    recommendation = evaluate_maintenance(16_093, "2026-08-01", **COROLLA)

    assert recommendation.evidence_market == "United States"
    assert recommendation.fallback_evidence is True
    assert recommendation.warnings == (
        "Evidence comes from the labeled United States fallback market",
    )
