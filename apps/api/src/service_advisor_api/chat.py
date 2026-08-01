import re
from dataclasses import dataclass

from service_advisor_api.providers import (
    DEFAULT_TIMEOUT_SECONDS,
    LanguageProvider,
    ProviderError,
)
from service_advisor_api.recommendations import Recommendation

ATTEMPTS = 2
DEGRADED_ANSWER = (
    "AI assistant temporarily unavailable; review the deterministic recommendation and citation."
)
_AMOUNT = re.compile(r"\d[\d,]*\.\d{2}|\$\s?\d")


@dataclass(frozen=True)
class ChatReply:
    text: str
    citation_page: int | None
    citation_section: str | None
    degraded: bool


def answer_contextual_question(
    question: str,
    recommendation: Recommendation,
    provider: LanguageProvider,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> ChatReply:
    """Answer from the model when it is usable, and from the evidence when it is not.

    One bounded retry, then degrade. Model text is only delivered if it survives the same
    grounding rules the deterministic answer obeys.
    """
    del question
    for _ in range(ATTEMPTS):
        try:
            answer = provider.complete(_prompt(recommendation), timeout_seconds=timeout_seconds)
        except ProviderError:
            continue
        if _is_grounded(answer, recommendation):
            return ChatReply(
                answer.strip(),
                recommendation.citation_page,
                recommendation.citation_section,
                False,
            )
        break
    return ChatReply(
        DEGRADED_ANSWER,
        recommendation.citation_page,
        recommendation.citation_section,
        True,
    )


def _prompt(recommendation: Recommendation) -> str:
    return (
        "Explica en espanol, en una frase, esta recomendacion de servicio. "
        "Usa solo estos hechos y no inventes precios ni urgencia. "
        f"Servicio: {recommendation.service_code}. Estado: {recommendation.state}. "
        f"Motivo: {recommendation.due_reason}. "
        f"Cita: pagina {recommendation.citation_page}, {recommendation.citation_section}."
    )


def _is_grounded(answer: str, recommendation: Recommendation) -> bool:
    """Model text may repeat the evidence; it may not add money or drop the service."""
    text = answer.strip()
    if not text or not text.isprintable():
        return False
    if _AMOUNT.search(text):
        return False
    return not (recommendation.service_code and recommendation.service_code not in text)
