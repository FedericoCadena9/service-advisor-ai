"""Against the real local model. Skipped when Ollama is not answering."""

import json
import urllib.error
import urllib.request

import pytest

from service_advisor_api.chat import answer_contextual_question
from service_advisor_api.providers import (
    OllamaProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
    select_provider,
)
from service_advisor_api.recommendations import evaluate_civic_maintenance


def _ollama_is_up() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            return bool(json.loads(response.read()).get("models"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


needs_ollama = pytest.mark.ollama(
    pytest.mark.skipif(not _ollama_is_up(), reason="Ollama is not running")
)
RECOMMENDATION = evaluate_civic_maintenance(48_000, "2026-07-31")


def test_a_refused_connection_is_reported_as_unavailable() -> None:
    """What if the host is wrong or the daemon is down? No network needed to prove this."""
    provider = OllamaProvider(host="http://127.0.0.1:1")

    with pytest.raises(ProviderUnavailableError):
        provider.complete("hola", timeout_seconds=2.0)


def test_an_impossible_budget_is_reported_as_a_timeout() -> None:
    provider = OllamaProvider(host="http://10.255.255.1")

    with pytest.raises((ProviderTimeoutError, ProviderUnavailableError)):
        provider.complete("hola", timeout_seconds=0.05)


def test_the_environment_selects_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADVISOR_PROVIDER", "ollama")

    assert isinstance(select_provider(), OllamaProvider)


@needs_ollama
def test_the_real_model_answers_the_prompt() -> None:
    answer = OllamaProvider().complete(
        "Responde unicamente con la palabra HONDA-A1.", timeout_seconds=60.0
    )

    assert answer.strip()


@needs_ollama
def test_a_real_timeout_degrades_instead_of_raising() -> None:
    """What if the model is slower than the Advisor's budget?"""
    reply = answer_contextual_question(
        "¿Por que?", RECOMMENDATION, OllamaProvider(), timeout_seconds=0.05
    )

    assert reply.degraded is True
    assert reply.citation_page == 42


@needs_ollama
def test_a_real_answer_is_still_held_to_the_grounding_rules() -> None:
    """The model may be right or wrong; either way the citation comes from the evidence."""
    reply = answer_contextual_question(
        "¿Por que es necesario?", RECOMMENDATION, OllamaProvider(), timeout_seconds=90.0
    )

    assert reply.citation_page == 42
    assert reply.citation_section == "Maintenance Minder"
    if not reply.degraded:
        assert "HONDA-A1" in reply.text
        assert ".00" not in reply.text
