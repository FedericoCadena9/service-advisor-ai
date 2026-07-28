from service_advisor_api.explanations import explain_recommendation
from service_advisor_api.recommendations import evaluate_civic_maintenance


def test_explanation_repeats_only_grounded_rule_outcome_and_citation() -> None:
    explanation = explain_recommendation(evaluate_civic_maintenance(48_000, "2026-07-27"))

    assert "HONDA-A1" in explanation.text
    assert explanation.citation_page == 42
    assert explanation.degraded is False


def test_unsupported_recommendation_never_becomes_actionable_explanation() -> None:
    explanation = explain_recommendation(evaluate_civic_maintenance(48_000, "2026-07-27", evidence_available=False))

    assert explanation.degraded is True
    assert "No actionable recommendation" in explanation.text
