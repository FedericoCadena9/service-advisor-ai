from dataclasses import dataclass
from typing import Literal

from service_advisor_api.knowledge import (
    EvidenceUnavailableError,
    KnowledgePack,
    MaintenanceRule,
)
from service_advisor_api.service_history import ServiceRecord

DueState = Literal["overdue", "due_now", "due_soon", "completed", "declined", "informational"]
CIVIC = {
    "make": "Honda",
    "model": "Civic",
    "engine": "2.0L",
    "drivetrain": "FWD",
    "market": "Mexico",
}


@dataclass(frozen=True)
class Recommendation:
    state: DueState
    actionable: bool
    service_code: str | None
    rule_version: str | None
    due_reason: str
    citation_page: int | None
    citation_section: str | None
    confidence: str
    warnings: tuple[str, ...]
    declined_service_ids: tuple[str, ...] = ()


def evaluate_maintenance(
    current_mileage_km: int,
    checked_in_on: str,
    *,
    make: str,
    model: str,
    engine: str,
    drivetrain: str,
    market: str,
    evidence_available: bool = True,
    completed_services: tuple[ServiceRecord, ...] = (),
    declined_services: tuple[ServiceRecord, ...] = (),
) -> Recommendation:
    """Evaluate one configuration against its own reviewed rule, never another one's."""
    del checked_in_on
    try:
        source, rule = KnowledgePack().rule_for(
            make=make, model=model, engine=engine, drivetrain=drivetrain, market=market
        )
    except EvidenceUnavailableError as error:
        return _insufficient(str(error))
    if not evidence_available or source.review_state != "reviewed":
        return _insufficient("Reviewed evidence is unavailable")

    relevant_declines = tuple(
        record.id for record in declined_services if record.service_code == rule.service_code
    )
    if any(record.service_code == rule.service_code for record in completed_services):
        return Recommendation("completed", False, rule.service_code, rule.version, "Equivalent service is completed", rule.citation_page, rule.citation_section, "high", (), relevant_declines)
    if relevant_declines:
        return Recommendation("declined", False, rule.service_code, rule.version, "Prior decline remains visible", rule.citation_page, rule.citation_section, "high", (), relevant_declines)

    state, reason = _due_state(current_mileage_km, rule)
    actionable = state != "informational"
    return Recommendation(
        state=state, actionable=actionable, service_code=rule.service_code if actionable else None,
        rule_version=rule.version if actionable else None, due_reason=reason,
        citation_page=rule.citation_page if actionable else None,
        citation_section=rule.citation_section if actionable else None,
        confidence="high" if actionable else "informational", warnings=(),
    )


def evaluate_civic_maintenance(
    current_mileage_km: int,
    checked_in_on: str,
    *,
    evidence_available: bool = True,
    completed_services: tuple[ServiceRecord, ...] = (),
    declined_services: tuple[ServiceRecord, ...] = (),
) -> Recommendation:
    return evaluate_maintenance(
        current_mileage_km,
        checked_in_on,
        **CIVIC,
        evidence_available=evidence_available,
        completed_services=completed_services,
        declined_services=declined_services,
    )


def _due_state(current_mileage_km: int, rule: MaintenanceRule) -> tuple[DueState, str]:
    if current_mileage_km > rule.interval_km + rule.overdue_grace_km:
        return "overdue", f"Mileage exceeds the {rule.interval_km:,} km interval"
    if current_mileage_km >= rule.interval_km:
        return "due_now", f"Mileage reached the {rule.interval_km:,} km interval"
    if current_mileage_km >= rule.interval_km - rule.due_soon_window_km:
        return "due_soon", f"Mileage is within {rule.due_soon_window_km:,} km of the interval"
    return "informational", "Mileage is not in the reviewed service window"


def _insufficient(warning: str) -> Recommendation:
    return Recommendation(
        state="informational", actionable=False, service_code=None, rule_version=None,
        due_reason="No actionable rule can be established", citation_page=None,
        citation_section=None, confidence="insufficient", warnings=(warning,),
    )
