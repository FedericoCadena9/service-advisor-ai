from dataclasses import dataclass

from service_advisor_api.recommendations import Recommendation


@dataclass(frozen=True)
class GroundedExplanation:
    text: str
    citation_page: int | None
    citation_section: str | None
    degraded: bool


def explain_recommendation(recommendation: Recommendation) -> GroundedExplanation:
    if not recommendation.actionable:
        return GroundedExplanation(
            "No actionable recommendation is available because reviewed evidence is insufficient or the work is historical.",
            recommendation.citation_page,
            recommendation.citation_section,
            True,
        )
    return GroundedExplanation(
        f"{recommendation.service_code} is {recommendation.state}: {recommendation.due_reason}.",
        recommendation.citation_page,
        recommendation.citation_section,
        False,
    )
