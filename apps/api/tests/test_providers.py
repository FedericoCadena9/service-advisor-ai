"""What the Advisor gets when the model is slow, absent, or wrong."""

import pytest

from service_advisor_api.chat import answer_contextual_question
from service_advisor_api.providers import (
    DeterministicProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
    select_provider,
)
from service_advisor_api.recommendations import evaluate_maintenance

COROLLA = {"make": "Toyota", "model": "Corolla", "engine": "2.0L", "drivetrain": "FWD", "market": "Mexico"}
RECOMMENDATION = evaluate_maintenance(16_093, "2026-08-01", **COROLLA)


class TimingOutProvider:
    name = "timing-out"

    def complete(self, prompt: str, *, timeout_seconds: float) -> str:
        raise ProviderTimeoutError(f"no answer within {timeout_seconds}s")


class RefusingProvider:
    name = "refusing"

    def complete(self, prompt: str, *, timeout_seconds: float) -> str:
        raise ProviderUnavailableError("connection refused")


class GarbageProvider:
    name = "garbage"

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, prompt: str, *, timeout_seconds: float) -> str:
        return self._text


class CountingProvider:
    name = "counting"

    def __init__(self, fail_times: int) -> None:
        self.calls = 0
        self._fail_times = fail_times

    def complete(self, prompt: str, *, timeout_seconds: float) -> str:
        self.calls += 1
        if self.calls <= self._fail_times:
            raise ProviderTimeoutError("slow")
        return "TOYOTA-10K esta vencido segun la evidencia citada."


def test_a_timeout_degrades_to_the_deterministic_answer() -> None:
    """What if the model never answers instead of answering late?"""
    reply = answer_contextual_question("¿Por que?", RECOMMENDATION, TimingOutProvider())

    assert reply.degraded is True
    assert reply.citation_page == 38
    assert "temporarily unavailable" in reply.text


def test_a_refused_connection_degrades_instead_of_raising() -> None:
    """What if the provider host is down instead of slow?"""
    reply = answer_contextual_question("¿Por que?", RECOMMENDATION, RefusingProvider())

    assert reply.degraded is True
    assert reply.citation_page == 38


@pytest.mark.parametrize(
    "text",
    ["", "   ", '{"partial": ', "\x00\x01garbage"],
    ids=["empty", "whitespace", "truncated-json", "binary-noise"],
)
def test_unusable_model_output_is_refused_rather_than_delivered(text: str) -> None:
    """What if the model answers with something that is not an answer?"""
    reply = answer_contextual_question("¿Por que?", RECOMMENDATION, GarbageProvider(text))

    assert reply.degraded is True
    assert reply.text.startswith("AI assistant temporarily unavailable")


def test_a_model_answer_that_invents_a_price_is_refused() -> None:
    """What if the model quotes a number the recommendation never carried?"""
    invented = "El servicio cuesta $9,999.00 MXN y debe hacerse hoy."

    reply = answer_contextual_question("¿Cuanto?", RECOMMENDATION, GarbageProvider(invented))

    assert reply.degraded is True
    assert "9,999" not in reply.text


def test_a_grounded_model_answer_is_delivered_with_its_citation() -> None:
    grounded = "El interval de 48,000 km se alcanzo, segun TOYOTA-10K."

    reply = answer_contextual_question("¿Por que?", RECOMMENDATION, GarbageProvider(grounded))

    assert reply.degraded is False
    assert reply.text == grounded
    assert reply.citation_page == 38


def test_the_retry_is_bounded_to_one_attempt() -> None:
    """What if the provider fails once instead of always — and what if it always does?"""
    recovering = CountingProvider(fail_times=1)
    always_failing = CountingProvider(fail_times=99)

    recovered = answer_contextual_question("¿Por que?", RECOMMENDATION, recovering)
    degraded = answer_contextual_question("¿Por que?", RECOMMENDATION, always_failing)

    assert recovered.degraded is False
    assert recovered.text == "TOYOTA-10K esta vencido segun la evidencia citada."
    assert recovering.calls == 2
    assert degraded.degraded is True
    assert always_failing.calls == 2


def test_the_deterministic_provider_needs_no_network() -> None:
    answer = DeterministicProvider().complete("anything", timeout_seconds=0.001)

    assert answer == ""


def test_the_default_selection_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    """What if nobody configured a provider — the demo must still answer."""
    monkeypatch.delenv("ADVISOR_PROVIDER", raising=False)

    assert isinstance(select_provider(), DeterministicProvider)


def test_an_unknown_provider_name_falls_back_instead_of_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What if the deployment sets a provider that does not exist?"""
    monkeypatch.setenv("ADVISOR_PROVIDER", "gpt-imaginary")

    assert isinstance(select_provider(), DeterministicProvider)
