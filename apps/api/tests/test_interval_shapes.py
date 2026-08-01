"""Manufacturers do not all schedule service the same way.

Toyota publishes a distance. Ford publishes a range plus an oil-life monitor. Honda
publishes no distance at all for its oil service: the Maintenance Minder decides. A single
`interval_km` integer could only represent the first, so the other two were being invented.
"""

import pytest

from service_advisor_api.knowledge import (
    ConditionInterval,
    FixedInterval,
    KnowledgePack,
    RangeInterval,
)


def test_a_fixed_interval_reads_as_before() -> None:
    interval = FixedInterval(km=16_093, due_soon_window_km=2_000, overdue_grace_km=2_000)

    assert interval.due_state(10_000) == ("informational", "Mileage is not in the reviewed service window")
    assert interval.due_state(14_093)[0] == "due_soon"
    assert interval.due_state(16_093)[0] == "due_now"
    assert interval.due_state(18_094)[0] == "overdue"


def test_a_range_is_due_across_its_whole_span() -> None:
    """What if the manual gives 12,000-16,000 km instead of a single number?"""
    interval = RangeInterval(earliest_km=12_000, latest_km=16_000, due_soon_window_km=800)

    assert interval.due_state(11_000)[0] == "informational"
    assert interval.due_state(11_200)[0] == "due_soon"
    assert interval.due_state(12_000)[0] == "due_now"
    assert interval.due_state(16_000)[0] == "due_now"
    assert interval.due_state(16_001)[0] == "overdue"


def test_a_range_states_its_span_in_the_reason() -> None:
    interval = RangeInterval(earliest_km=12_000, latest_km=16_000)

    _, reason = interval.due_state(13_000)

    assert "12,000" in reason
    assert "16,000" in reason


def test_a_condition_based_interval_refuses_to_guess_from_distance() -> None:
    """What if the manufacturer schedules by oil life instead of by odometer?"""
    interval = ConditionInterval(monitor="Maintenance Minder")

    state, reason = interval.due_state(48_000)

    assert state == "informational"
    assert "Maintenance Minder" in reason
    assert "distance" in reason


def test_every_reviewed_rule_carries_a_real_source() -> None:
    """No invented provenance: each rule names a document, a page and a retrieval date."""
    for configuration in KnowledgePack().configurations():
        source = configuration.source
        assert source.source_url.startswith("https://")
        assert source.citation_page
        assert source.citation_section
        assert source.retrieval_date == "2026-07-31"
        assert source.checksum


def test_no_configuration_claims_a_verified_mexican_document() -> None:
    """The research found no public Mexican schedule binding model, engine and drivetrain."""
    for configuration in KnowledgePack().configurations():
        assert configuration.source.fallback_market is True
        assert configuration.source.market == "United States"


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("Civic", ConditionInterval),
        ("CR-V", ConditionInterval),
        ("Accord", ConditionInterval),
        ("Corolla", FixedInterval),
        ("RAV4", FixedInterval),
        ("Tacoma", FixedInterval),
        ("F-150", RangeInterval),
        ("Escape", RangeInterval),
        ("Explorer", RangeInterval),
        ("Ranger", RangeInterval),
    ],
)
def test_each_model_uses_the_shape_its_manual_publishes(model: str, expected: type) -> None:
    configurations = [
        configuration
        for configuration in KnowledgePack().configurations()
        if configuration.model == model
    ]

    assert configurations
    assert all(isinstance(item.rule.interval, expected) for item in configurations)
