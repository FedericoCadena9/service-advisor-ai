from service_advisor_api.recommendations import evaluate_civic_maintenance


def test_mileage_boundary_returns_due_now_with_exact_rule_evidence() -> None:
    recommendation = evaluate_civic_maintenance(current_mileage_km=48_000, checked_in_on="2026-07-27")

    assert recommendation.state == "due_now"
    assert recommendation.actionable is True
    assert recommendation.service_code == "HONDA-A1"
    assert recommendation.rule_version == "honda-civic-2019-lx-v1"
    assert recommendation.citation_page == 42
    assert recommendation.citation_section == "Maintenance Minder"


def test_mileage_overdue_and_due_soon_boundaries_are_deterministic() -> None:
    assert evaluate_civic_maintenance(50_001, "2026-07-27").state == "overdue"
    assert evaluate_civic_maintenance(47_000, "2026-07-27").state == "due_soon"


def test_unsupported_evidence_is_informational_not_actionable() -> None:
    recommendation = evaluate_civic_maintenance(48_000, "2026-07-27", evidence_available=False)

    assert recommendation.state == "informational"
    assert recommendation.actionable is False
    assert "Reviewed evidence is unavailable" in recommendation.warnings
