from service_advisor_api.workflows import AdvisorWorkflowStore


def test_run_reconnect_reuses_checkpoint_without_repeating_reads() -> None:
    store = AdvisorWorkflowStore()
    run = store.start("demo-shop", "session-a")
    reconnected = store.reconnect(run.id, "demo-shop", "session-a")

    assert reconnected.id == run.id
    assert reconnected.events == ("started", "context_loaded", "awaiting_human_review")


def test_decision_is_idempotent_and_no_command_runs_before_approval() -> None:
    store = AdvisorWorkflowStore()
    run = store.start("demo-shop", "session-a")

    first = store.decide(run.id, "approve")
    repeated = store.decide(run.id, "approve")

    assert first == repeated
    assert first.command_executed is True
