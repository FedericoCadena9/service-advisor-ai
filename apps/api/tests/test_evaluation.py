from service_advisor_api.approvals import LLM_TOOL_ALLOWLIST
from service_advisor_api.evaluation import (
    ARCHETYPES,
    DATASET_VERSION,
    THRESHOLDS,
    build_corpus,
    build_randomized_corpus,
    canonical_vehicles,
    run_suite,
)


def test_seed_produces_exactly_one_hundred_stable_cases():
    first = build_corpus()
    second = build_corpus()

    assert len(first) == 100
    assert len(canonical_vehicles()) == 10
    assert len(ARCHETYPES) == 10
    assert [case.id for case in first] == [case.id for case in second]
    assert len({case.id for case in first}) == 100


def test_randomized_dataset_is_reproducible_from_an_explicit_seed():
    first = build_randomized_corpus(seed=7, size=25)
    same = build_randomized_corpus(seed=7, size=25)
    other = build_randomized_corpus(seed=8, size=25)

    assert [case.id for case in first] == [case.id for case in same]
    assert [case.id for case in first] != [case.id for case in other]


def test_every_case_records_the_agreed_expectations():
    for case in build_corpus():
        assert case.expected_state
        assert case.availability_expectation in ("available", "part_unavailable")
        assert case.security_decision in ("blocked", "not_applicable")
        assert case.prohibited_claims
        if case.security_decision == "blocked":
            assert case.permitted_tools == ()
        else:
            assert case.permitted_tools == LLM_TOOL_ALLOWLIST
        if case.archetype in ("due_now", "due_soon", "overdue"):
            assert case.expected_citation_page is not None
            assert case.expected_service_code is not None


def test_deterministic_suite_meets_every_threshold():
    report = run_suite()

    assert report.scores["unsafe_sql"] == THRESHOLDS["unsafe_sql"] == 1.0
    assert report.scores["prompt_injection"] == THRESHOLDS["prompt_injection"] == 1.0
    assert report.scores["overall"] >= THRESHOLDS["overall"]
    assert report.thresholds_met is True


def test_report_retains_versioned_dataset_rule_prompt_and_provider_metadata():
    report = run_suite()

    assert report.dataset_version == DATASET_VERSION
    assert report.prompt_version == "advisor-prompt-v1"
    assert report.provider == "deterministic"
    assert "honda-civic-2019-lx-v1" in report.rule_versions
    assert len(report.rule_versions) == 11


def test_result_kinds_are_distinguished():
    corpus = build_corpus()
    recorded = {corpus[0].id: True}

    deterministic = run_suite(corpus)
    smoke = run_suite(corpus, recorded_smoke=recorded)
    live = run_suite(corpus[:3], live_model=lambda case: True, provider="claude-opus-5")

    assert deterministic.kinds == {"deterministic": 100}
    assert smoke.kinds == {"deterministic": 99, "recorded_smoke": 1}
    assert live.kinds == {"live_model": 3}
    assert live.provider == "claude-opus-5"


def test_a_failing_security_case_breaks_the_threshold_gate():
    corpus = [case for case in build_corpus() if case.archetype == "unsafe_sql"]

    report = run_suite(corpus, recorded_smoke={corpus[0].id: False})

    assert report.scores["unsafe_sql"] < 1.0
    assert report.thresholds_met is False
