from service_advisor_api.explanations import explain_recommendation
from service_advisor_api.recommendations import evaluate_maintenance

COROLLA = {"make": "Toyota", "model": "Corolla", "engine": "2.0L", "drivetrain": "FWD", "market": "Mexico"}


def test_explanation_repeats_only_grounded_rule_outcome_and_citation() -> None:
    explanation = explain_recommendation(evaluate_maintenance(16_093, "2026-08-01", **COROLLA))

    assert "TOYOTA-10K" in explanation.text
    assert explanation.citation_page == 38
    assert explanation.degraded is False


def test_unsupported_recommendation_never_becomes_actionable_explanation() -> None:
    explanation = explain_recommendation(evaluate_maintenance(16_093, "2026-08-01", **COROLLA, evidence_available=False))

    assert explanation.degraded is True
    assert "No actionable recommendation" in explanation.text
