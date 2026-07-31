import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256

from service_advisor_api.operations import BaySlot, PartAvailability

IVA_RATE = Decimal("0.16")
CENTAVO = Decimal("0.01")


class UnknownServiceError(ValueError):
    """Raised when a requested service is outside the reviewed catalog."""


class InformationalServiceError(ValueError):
    """Raised when an informational-only service is drafted as billable work."""


@dataclass(frozen=True)
class LaborOperation:
    code: str
    price_mxn: Decimal
    duration_minutes: int


@dataclass(frozen=True)
class PartRequirement:
    part_number: str
    unit_price_mxn: Decimal
    quantity: int


@dataclass(frozen=True)
class QuotableService:
    service_code: str
    labor: tuple[LaborOperation, ...]
    parts: tuple[PartRequirement, ...]
    fits_engines: tuple[str, ...]
    informational_only: bool = False


@dataclass(frozen=True)
class QuoteLine:
    service_code: str
    labor_mxn: Decimal
    parts_mxn: Decimal
    iva_mxn: Decimal
    total_mxn: Decimal
    duration_minutes: int
    fitment: str
    available: bool
    unavailable_reason: str | None


@dataclass(frozen=True)
class QuoteDraft:
    lines: tuple[QuoteLine, ...]
    subtotal_mxn: Decimal
    iva_mxn: Decimal
    total_mxn: Decimal
    duration_minutes: int
    bay_slot_id: str | None
    warnings: tuple[str, ...]


SERVICE_CATALOG: dict[str, QuotableService] = {
    "HONDA-A1": QuotableService(
        service_code="HONDA-A1",
        labor=(
            LaborOperation("LUBE-OIL", Decimal("380.00"), 30),
            LaborOperation("TIRE-ROTATE", Decimal("240.00"), 20),
        ),
        parts=(
            PartRequirement("HON-OIL-0W20", Decimal("189.50"), 4),
            PartRequirement("HON-FILTER-15400", Decimal("215.00"), 1),
        ),
        fits_engines=("2.0L",),
    ),
    "HONDA-TIRE-ROTATION": QuotableService(
        service_code="HONDA-TIRE-ROTATION",
        labor=(LaborOperation("TIRE-ROTATE", Decimal("240.00"), 20),),
        parts=(),
        fits_engines=("2.0L", "1.5T"),
    ),
    "HONDA-CABIN-FILTER": QuotableService(
        service_code="HONDA-CABIN-FILTER",
        labor=(LaborOperation("CABIN-FILTER", Decimal("160.00"), 15),),
        parts=(PartRequirement("HON-CABIN-80292", Decimal("410.00"), 1),),
        fits_engines=("2.0L",),
    ),
    "HONDA-BRAKE-PADS-FRONT": QuotableService(
        service_code="HONDA-BRAKE-PADS-FRONT",
        labor=(LaborOperation("BRAKE-FRONT", Decimal("980.00"), 75),),
        parts=(PartRequirement("HON-BRAKE-45022", Decimal("2450.00"), 1),),
        fits_engines=("2.0L",),
    ),
    "HONDA-TURBO-COOLANT": QuotableService(
        service_code="HONDA-TURBO-COOLANT",
        labor=(LaborOperation("COOLANT-TURBO", Decimal("640.00"), 45),),
        parts=(),
        fits_engines=("1.5T",),
    ),
    "HONDA-MULTIPOINT-INSPECTION": QuotableService(
        service_code="HONDA-MULTIPOINT-INSPECTION",
        labor=(),
        parts=(),
        fits_engines=("2.0L", "1.5T"),
        informational_only=True,
    ),
}


def catalog_service(service_code: str) -> QuotableService:
    try:
        return SERVICE_CATALOG[service_code]
    except KeyError as error:
        raise UnknownServiceError(f"{service_code} is outside the reviewed catalog") from error


def required_part_numbers(service_codes: Sequence[str]) -> tuple[str, ...]:
    numbers: list[str] = []
    for service_code in service_codes:
        for requirement in catalog_service(service_code).parts:
            if requirement.part_number not in numbers:
                numbers.append(requirement.part_number)
    return tuple(numbers)


def draft_quote(
    service_codes: Sequence[str],
    *,
    engine: str,
    parts: Mapping[str, PartAvailability | None],
    slots: Sequence[BaySlot],
) -> QuoteDraft:
    """Price a de-duplicated bundle against tenant-scoped availability."""
    services = [catalog_service(service_code) for service_code in service_codes]
    informational = [service.service_code for service in services if service.informational_only]
    if informational:
        raise InformationalServiceError(
            f"{', '.join(informational)} is informational only and cannot be quoted"
        )

    charged_labor: set[str] = set()
    charged_parts: dict[str, int] = {}
    lines: list[QuoteLine] = []
    for service in services:
        lines.append(_price_service(service, engine, parts, charged_labor, charged_parts))

    billable = [line for line in lines if line.available]
    subtotal = sum((line.labor_mxn + line.parts_mxn for line in billable), Decimal("0.00"))
    iva = sum((line.iva_mxn for line in billable), Decimal("0.00"))
    duration = sum(line.duration_minutes for line in billable)
    slot = next((slot for slot in slots if slot.capacity_minutes >= duration), None)
    warnings: tuple[str, ...] = ()
    if billable and slot is None:
        warnings = ("No bay slot has capacity for the drafted duration",)
    return QuoteDraft(
        lines=tuple(lines),
        subtotal_mxn=_money(subtotal),
        iva_mxn=_money(iva),
        total_mxn=_money(subtotal + iva),
        duration_minutes=duration,
        bay_slot_id=slot.id if slot else None,
        warnings=warnings,
    )


def fingerprint(draft: QuoteDraft) -> str:
    """Hash every volatile input an approval depends on: price, availability, and slot."""
    volatile = {
        "lines": [
            {
                "service_code": line.service_code,
                "labor_mxn": str(line.labor_mxn),
                "parts_mxn": str(line.parts_mxn),
                "total_mxn": str(line.total_mxn),
                "duration_minutes": line.duration_minutes,
                "available": line.available,
                "unavailable_reason": line.unavailable_reason,
            }
            for line in draft.lines
        ],
        "total_mxn": str(draft.total_mxn),
        "duration_minutes": draft.duration_minutes,
        "bay_slot_id": draft.bay_slot_id,
    }
    return sha256(json.dumps(volatile, sort_keys=True).encode()).hexdigest()


def _price_service(
    service: QuotableService,
    engine: str,
    parts: Mapping[str, PartAvailability | None],
    charged_labor: set[str],
    charged_parts: dict[str, int],
) -> QuoteLine:
    if engine not in service.fits_engines:
        return _unavailable_line(
            service, "not_applicable", f"Service does not fit the {engine} engine"
        )

    for requirement in service.parts:
        reason = _part_blocker(requirement, parts.get(requirement.part_number))
        if reason is not None:
            return _unavailable_line(service, "confirmed", reason)

    labor = sum(
        (operation.price_mxn for operation in service.labor if operation.code not in charged_labor),
        Decimal("0.00"),
    )
    duration = sum(
        operation.duration_minutes
        for operation in service.labor
        if operation.code not in charged_labor
    )
    charged_labor.update(operation.code for operation in service.labor)

    parts_total = Decimal("0.00")
    for requirement in service.parts:
        already_charged = charged_parts.get(requirement.part_number, 0)
        billable_quantity = max(requirement.quantity - already_charged, 0)
        parts_total += requirement.unit_price_mxn * billable_quantity
        charged_parts[requirement.part_number] = max(already_charged, requirement.quantity)

    subtotal = _money(labor + parts_total)
    iva = _money(subtotal * IVA_RATE)
    return QuoteLine(
        service_code=service.service_code,
        labor_mxn=_money(labor),
        parts_mxn=_money(parts_total),
        iva_mxn=iva,
        total_mxn=_money(subtotal + iva),
        duration_minutes=duration,
        fitment="confirmed",
        available=True,
        unavailable_reason=None,
    )


def _part_blocker(requirement: PartRequirement, availability: PartAvailability | None) -> str | None:
    if availability is None:
        return f"Part {requirement.part_number} is not carried by this shop"
    if availability.on_hand >= requirement.quantity:
        return None
    if availability.restock_eta is not None:
        return (
            f"Part {requirement.part_number} is {availability.restock_status} "
            f"until {availability.restock_eta}"
        )
    return f"Part {requirement.part_number} is {availability.restock_status} with no restock date"


def _unavailable_line(service: QuotableService, fitment: str, reason: str) -> QuoteLine:
    return QuoteLine(
        service_code=service.service_code,
        labor_mxn=Decimal("0.00"),
        parts_mxn=Decimal("0.00"),
        iva_mxn=Decimal("0.00"),
        total_mxn=Decimal("0.00"),
        duration_minutes=0,
        fitment=fitment,
        available=False,
        unavailable_reason=reason,
    )


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(CENTAVO, rounding=ROUND_HALF_UP)
