from decimal import Decimal

import pytest

from service_advisor_api.observability import (
    REDACTED,
    TraceRecorder,
    TraceVersions,
    quality_dashboard,
    redact_attributes,
    redact_value,
)

VERSIONS = TraceVersions(
    rule_version="honda-civic-2019-lx-v1",
    prompt_version="advisor-prompt-v1",
    dataset_version="canonical-100-v1",
    model="deterministic-demo",
)
PROHIBITED = {
    "customer_name": "Demo Customer",
    "phone": "+52 55 0000 0000",
    "email": "cliente@example.com",
    "vin": "1HGBH41JXMN109186",
    "plate": "ABC-123-A",
    "transcript": "El cliente reporta un ruido",
    "message_text": "Hola Demo Customer",
    "audio_reference": "s3://bucket/audio.wav",
    "concern": "Rechinido al frenar",
}


def _recorder() -> tuple[TraceRecorder, str]:
    recorder = TraceRecorder()
    return recorder, recorder.start_trace("demo-shop", VERSIONS)


def test_run_emits_correlated_spans_of_every_kind():
    recorder, trace_id = _recorder()
    for name, kind in (
        ("POST /advisor-runs", "http"),
        ("advisor_run.start", "workflow"),
        ("read_recommendation", "tool"),
        ("knowledge.retrieval", "retrieval"),
        ("contextual_chat", "provider"),
        ("approve_quote", "command"),
    ):
        recorder.record(trace_id, name=name, kind=kind, latency_ms=10.0)

    export = recorder.export(trace_id, "demo-shop")

    assert {span["kind"] for span in export["spans"]} == {
        "http",
        "workflow",
        "tool",
        "retrieval",
        "provider",
        "command",
    }
    assert all(span.trace_id == trace_id for span in recorder.spans(trace_id, "demo-shop"))
    assert export["versions"]["dataset_version"] == "canonical-100-v1"
    assert export["versions"]["model"] == "deterministic-demo"


def test_spans_record_latency_and_cost():
    recorder, trace_id = _recorder()

    recorder.record(
        trace_id,
        name="contextual_chat",
        kind="provider",
        latency_ms=42.5,
        cost_mxn=Decimal("0.0125"),
    )

    (span,) = recorder.export(trace_id, "demo-shop")["spans"]
    assert span["latency_ms"] == 42.5
    assert span["cost_mxn"] == "0.0125"


def test_prohibited_attributes_never_reach_a_span():
    recorder, trace_id = _recorder()

    recorder.record(
        trace_id,
        name="knowledge.retrieval",
        kind="retrieval",
        latency_ms=5.0,
        attributes={**PROHIBITED, "citation_page": 42},
    )

    export = recorder.export(trace_id, "demo-shop")
    payload = str(export)
    for prohibited in PROHIBITED.values():
        assert prohibited not in payload
    assert export["spans"][0]["attributes"] == {"citation_page": 42}


def test_free_text_identifiers_are_scrubbed():
    assert redact_value("Contact cliente@example.com or +52 55 0000 0000") == (
        f"Contact {REDACTED} or {REDACTED}"
    )
    assert redact_value("VIN 1HGBH41JXMN109186 plate ABC-123-A") == (
        f"VIN {REDACTED} plate {REDACTED}"
    )
    assert redact_attributes({"note": "call +52 55 1234 5678"}) == {"note": f"call {REDACTED}"}


def test_unknown_span_kind_is_refused():
    recorder, trace_id = _recorder()

    with pytest.raises(ValueError, match="is not a recorded span kind"):
        recorder.record(trace_id, name="unknown", kind="database", latency_ms=1.0)


def test_traces_are_scoped_to_the_shop():
    recorder, trace_id = _recorder()

    with pytest.raises(PermissionError):
        recorder.spans(trace_id, "another-shop")


def test_dashboard_reports_quality_evaluation_and_escalation_outcomes():
    recorder, trace_id = _recorder()
    recorder.record(
        trace_id,
        name="knowledge.retrieval",
        kind="retrieval",
        latency_ms=10.0,
        attributes={"citation_page": 42},
    )
    recorder.record(
        trace_id,
        name="knowledge.retrieval",
        kind="retrieval",
        latency_ms=30.0,
        attributes={"citation_page": None},
    )
    recorder.record(
        trace_id,
        name="contextual_chat",
        kind="provider",
        latency_ms=50.0,
        cost_mxn=Decimal("0.0125"),
    )

    dashboard = quality_dashboard(
        recorder,
        "demo-shop",
        escalation_outcomes={"approved": 2, "rejected": 1, "escalated": 1},
        evaluation_thresholds_met=True,
        evaluation_score=1.0,
    )

    assert dashboard["citation_rate"] == 0.5
    assert dashboard["spans_by_kind"]["retrieval"] == 2
    assert dashboard["total_cost_mxn"] == "0.0125"
    assert dashboard["p50_latency_ms"] == 30.0
    assert dashboard["p95_latency_ms"] == 50.0
    assert dashboard["escalation_outcomes"]["escalated"] == 1
    assert dashboard["evaluation_thresholds_met"] is True
