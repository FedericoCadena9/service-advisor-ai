from service_advisor_api.recommendations import evaluate_civic_maintenance
from service_advisor_api.service_history import CivicServiceHistoryStore


def test_completed_equivalent_service_suppresses_duplicate_recommendation() -> None:
    history = CivicServiceHistoryStore()
    history.seed()

    recommendation = evaluate_civic_maintenance(
        50_001, "2026-07-27", completed_services=history.completed("demo-shop", "honda-civic-2019-lx")
    )

    assert recommendation.state == "completed"
    assert recommendation.actionable is False


def test_declined_work_remains_visible_and_auditable() -> None:
    history = CivicServiceHistoryStore()
    history.seed()

    recommendation = evaluate_civic_maintenance(
        48_000, "2026-07-27", declined_services=history.declined("demo-shop", "honda-civic-2019-lx")
    )

    assert recommendation.state == "declined"
    assert recommendation.declined_service_ids == ("decline-honda-a1-2026-06",)
