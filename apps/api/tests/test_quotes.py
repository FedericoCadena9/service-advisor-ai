from decimal import Decimal

import pytest

from service_advisor_api.operations import BaySlot, PartAvailability
from service_advisor_api.quotes import (
    IVA_RATE,
    InformationalServiceError,
    UnknownServiceError,
    draft_quote,
    required_part_numbers,
)

STOCKED_PARTS = {
    "HON-OIL-0W20": PartAvailability("HON-OIL-0W20", 12, "in_stock", None),
    "HON-FILTER-15400": PartAvailability("HON-FILTER-15400", 4, "in_stock", None),
    "HON-CABIN-80292": PartAvailability("HON-CABIN-80292", 0, "backordered", "2026-08-14"),
    "HON-BRAKE-45022": PartAvailability("HON-BRAKE-45022", 0, "discontinued", None),
}
SLOTS = (
    BaySlot("bay-1-morning", "2026-08-03T09:00:00", 90),
    BaySlot("bay-2-afternoon", "2026-08-03T14:00:00", 180),
)


def test_line_shows_labor_parts_iva_total_duration_and_fitment():
    draft = draft_quote(["HONDA-A1"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS)

    (line,) = draft.lines
    assert line.labor_mxn == Decimal("620.00")
    assert line.parts_mxn == Decimal("973.00")
    assert line.iva_mxn == Decimal("254.88")
    assert line.total_mxn == Decimal("1847.88")
    assert line.duration_minutes == 50
    assert line.fitment == "confirmed"
    assert line.unavailable_reason is None


def test_iva_rounds_half_up_at_the_centavo_boundary():
    below = (Decimal("1150.03") * IVA_RATE).quantize(Decimal("0.01"))
    above = (Decimal("1150.04") * IVA_RATE).quantize(Decimal("0.01"))

    assert (below, above) == (Decimal("184.00"), Decimal("184.01"))


def test_bundle_charges_shared_labor_once():
    draft = draft_quote(
        ["HONDA-A1", "HONDA-TIRE-ROTATION"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS
    )

    rotation = draft.lines[1]
    assert rotation.labor_mxn == Decimal("0.00")
    assert rotation.duration_minutes == 0
    assert draft.duration_minutes == 50


def test_unfitted_service_reports_an_explicit_reason():
    draft = draft_quote(["HONDA-TURBO-COOLANT"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS)

    (line,) = draft.lines
    assert line.available is False
    assert line.fitment == "not_applicable"
    assert line.unavailable_reason == "Service does not fit the 2.0L engine"
    assert draft.total_mxn == Decimal("0.00")


def test_backordered_part_reports_restock_status_and_eta():
    draft = draft_quote(["HONDA-CABIN-FILTER"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS)

    (line,) = draft.lines
    assert line.available is False
    assert line.unavailable_reason == "Part HON-CABIN-80292 is backordered until 2026-08-14"


def test_part_without_restock_date_reports_no_restock_date():
    draft = draft_quote(["HONDA-BRAKE-PADS-FRONT"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS)

    (line,) = draft.lines
    assert line.unavailable_reason == "Part HON-BRAKE-45022 is discontinued with no restock date"


def test_unavailable_lines_are_excluded_from_totals_and_duration():
    draft = draft_quote(
        ["HONDA-A1", "HONDA-CABIN-FILTER"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS
    )

    assert draft.subtotal_mxn == Decimal("1593.00")
    assert draft.total_mxn == Decimal("1847.88")
    assert draft.duration_minutes == 50


def test_draft_reserves_the_first_slot_with_enough_capacity():
    draft = draft_quote(["HONDA-BRAKE-PADS-FRONT", "HONDA-A1"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS)

    assert draft.bay_slot_id == "bay-1-morning"


def test_draft_warns_when_no_bay_slot_has_capacity():
    draft = draft_quote(
        ["HONDA-A1"],
        engine="2.0L",
        parts=STOCKED_PARTS,
        slots=(BaySlot("bay-3-short", "2026-08-03T17:00:00", 20),),
    )

    assert draft.bay_slot_id is None
    assert draft.warnings == ("No bay slot has capacity for the drafted duration",)


def test_informational_service_cannot_be_quoted():
    with pytest.raises(InformationalServiceError):
        draft_quote(
            ["HONDA-MULTIPOINT-INSPECTION"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS
        )


def test_unknown_service_is_rejected():
    with pytest.raises(UnknownServiceError):
        draft_quote(["HONDA-UNREVIEWED"], engine="2.0L", parts=STOCKED_PARTS, slots=SLOTS)


def test_required_part_numbers_are_deduplicated_for_availability_lookup():
    assert required_part_numbers(["HONDA-A1", "HONDA-TIRE-ROTATION"]) == (
        "HON-OIL-0W20",
        "HON-FILTER-15400",
    )
