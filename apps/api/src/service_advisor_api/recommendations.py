from dataclasses import dataclass
from typing import Literal

from service_advisor_api.knowledge import KnowledgePack
from service_advisor_api.service_history import ServiceRecord

DueState = Literal["overdue", "due_now", "due_soon", "completed", "declined", "informational"]


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


def evaluate_civic_maintenance(
    current_mileage_km: int,
    checked_in_on: str,
    *,
    evidence_available: bool = True,
    completed_services: tuple[ServiceRecord, ...] = (),
    declined_services: tuple[ServiceRecord, ...] = (),
) -> Recommendation:
    del checked_in_on
    source, rule = KnowledgePack().reviewed_civic_rule()
    if not evidence_available or source.review_state != "reviewed":
        return Recommendation(
            state="informational", actionable=False, service_code=None, rule_version=None,
            due_reason="No actionable rule can be established", citation_page=None,
            citation_section=None, confidence="insufficient", warnings=("Reviewed evidence is unavailable",),
        )
    relevant_declines = tuple(record.id for record in declined_services if record.service_code == rule.service_code)
    if any(record.service_code == rule.service_code for record in completed_services):
        return Recommendation("completed", False, rule.service_code, rule.version, "Equivalent service is completed", rule.citation_page, rule.citation_section, "high", (), relevant_declines)
    if relevant_declines:
        return Recommendation("declined", False, rule.service_code, rule.version, "Prior decline remains visible", rule.citation_page, rule.citation_section, "high", (), relevant_declines)
    if current_mileage_km > 50_000:
        state, reason = "overdue", "Mileage exceeds the 50,000 km interval"
    elif current_mileage_km >= 48_000:
        state, reason = "due_now", "Mileage reached the 48,000 km interval"
    elif current_mileage_km >= 46_000:
        state, reason = "due_soon", "Mileage is within 2,000 km of the interval"
    else:
        state, reason = "informational", "Mileage is not in the reviewed service window"
    actionable = state != "informational"
    return Recommendation(
        state=state, actionable=actionable, service_code=rule.service_code if actionable else None,
        rule_version=rule.version if actionable else None, due_reason=reason,
        citation_page=rule.citation_page if actionable else None,
        citation_section=rule.citation_section if actionable else None,
        confidence="high" if actionable else "informational", warnings=(),
    )
