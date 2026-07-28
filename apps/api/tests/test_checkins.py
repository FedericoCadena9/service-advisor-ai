import pytest

from service_advisor_api.checkins import InvalidCheckinError, validate_checkin


def test_normal_use_checkin_preserves_all_agreed_fields() -> None:
    checkin = validate_checkin(
        current_mileage_km=43_000,
        prior_mileage_km=42_500,
        checked_in_on="2026-07-27",
        use_profile="normal",
        severe_use_factors=[],
        concern="Brake pedal feels soft in traffic",
        appointment_window="2026-07-28 morning",
        message_consent=True,
    )

    assert checkin.current_mileage_km == 43_000
    assert checkin.use_profile == "normal"
    assert checkin.severe_use_factors == ()
    assert checkin.message_consent is True


def test_severe_use_checkin_requires_at_least_one_factor() -> None:
    with pytest.raises(InvalidCheckinError, match="severe-use factor"):
        validate_checkin(
            current_mileage_km=43_000,
            prior_mileage_km=42_500,
            checked_in_on="2026-07-27",
            use_profile="severe",
            severe_use_factors=[],
            concern="Routine service",
            appointment_window="2026-07-28 morning",
            message_consent=False,
        )


def test_checkin_rejects_mileage_below_prior_record() -> None:
    with pytest.raises(InvalidCheckinError, match="prior recorded mileage"):
        validate_checkin(
            current_mileage_km=42_499,
            prior_mileage_km=42_500,
            checked_in_on="2026-07-27",
            use_profile="normal",
            severe_use_factors=[],
            concern="Routine service",
            appointment_window="2026-07-28 morning",
            message_consent=False,
        )
