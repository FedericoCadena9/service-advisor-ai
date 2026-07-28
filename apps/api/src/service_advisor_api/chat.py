from dataclasses import dataclass

from service_advisor_api.recommendations import Recommendation


@dataclass(frozen=True)
class ChatReply:
    text: str
    citation_page: int | None
    citation_section: str | None
    degraded: bool


def answer_contextual_question(question: str, recommendation: Recommendation, provider_available: bool) -> ChatReply:
    del question
    for _ in range(2):
        if provider_available:
            return ChatReply(
                f"{recommendation.due_reason} This is supported by {recommendation.service_code}.",
                recommendation.citation_page,
                recommendation.citation_section,
                False,
            )
    return ChatReply("AI assistant temporarily unavailable; review the deterministic recommendation and citation.", recommendation.citation_page, recommendation.citation_section, True)
