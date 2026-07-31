import re
from dataclasses import dataclass, field
from decimal import Decimal
from threading import RLock
from uuid import uuid4

SPAN_KINDS = ("http", "workflow", "tool", "retrieval", "provider", "command")
DENIED_ATTRIBUTES = frozenset(
    {
        "customer_name",
        "customer_label",
        "phone",
        "email",
        "vin",
        "plate",
        "concern",
        "transcript",
        "raw_transcript",
        "message_text",
        "sms_text",
        "audio",
        "audio_reference",
    }
)
REDACTED = "[redacted]"
_PATTERNS = (
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    re.compile(r"\+?\d[\d\s().-]{7,}\d"),
    re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b"),
    re.compile(r"\b[A-Z]{3}-\d{3}-[A-Z]\b"),
    re.compile(r"\b[A-Z]{3}-\d{2}-\d{2}\b"),
)


@dataclass(frozen=True)
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    kind: str
    latency_ms: float
    cost_mxn: Decimal
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceVersions:
    rule_version: str | None
    prompt_version: str
    dataset_version: str
    model: str


def redact_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in _PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact_attributes(attributes: dict[str, object]) -> dict[str, object]:
    """Source-side redaction: prohibited fields never enter an exported span."""
    return {
        key: redact_value(value)
        for key, value in attributes.items()
        if key not in DENIED_ATTRIBUTES
    }


class TraceRecorder:
    """Correlated spans for one Advisor Run, redacted before export."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._spans: dict[str, list[Span]] = {}
        self._versions: dict[str, TraceVersions] = {}
        self._shops: dict[str, str] = {}

    def start_trace(self, shop_id: str, versions: TraceVersions) -> str:
        trace_id = str(uuid4())
        with self._lock:
            self._spans[trace_id] = []
            self._versions[trace_id] = versions
            self._shops[trace_id] = shop_id
        return trace_id

    def record(
        self,
        trace_id: str,
        *,
        name: str,
        kind: str,
        latency_ms: float,
        cost_mxn: Decimal = Decimal("0.0000"),
        parent_span_id: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> Span | None:
        if kind not in SPAN_KINDS:
            raise ValueError(f"{kind} is not a recorded span kind")
        with self._lock:
            if trace_id not in self._spans:
                return None
            span = Span(
                trace_id=trace_id,
                span_id=str(uuid4()),
                parent_span_id=parent_span_id,
                name=name,
                kind=kind,
                latency_ms=latency_ms,
                cost_mxn=cost_mxn,
                attributes=redact_attributes(attributes or {}),
            )
            self._spans[trace_id].append(span)
            return span

    def spans(self, trace_id: str, shop_id: str) -> tuple[Span, ...]:
        with self._lock:
            if self._shops.get(trace_id) != shop_id:
                raise PermissionError("Trace is outside this shop")
            return tuple(self._spans.get(trace_id, ()))

    def versions(self, trace_id: str) -> TraceVersions | None:
        return self._versions.get(trace_id)

    def traces(self, shop_id: str) -> tuple[str, ...]:
        with self._lock:
            return tuple(
                trace_id for trace_id, shop in self._shops.items() if shop == shop_id
            )

    def export(self, trace_id: str, shop_id: str) -> dict[str, object]:
        spans = self.spans(trace_id, shop_id)
        versions = self.versions(trace_id)
        return {
            "trace_id": trace_id,
            "versions": versions.__dict__ if versions else {},
            "spans": [
                {
                    "span_id": span.span_id,
                    "parent_span_id": span.parent_span_id,
                    "name": span.name,
                    "kind": span.kind,
                    "latency_ms": span.latency_ms,
                    "cost_mxn": str(span.cost_mxn),
                    "attributes": span.attributes,
                }
                for span in spans
            ],
        }


def quality_dashboard(
    recorder: TraceRecorder,
    shop_id: str,
    *,
    escalation_outcomes: dict[str, int],
    evaluation_thresholds_met: bool,
    evaluation_score: float,
) -> dict[str, object]:
    """Manager and Admin quality view built only from redacted spans."""
    spans = [span for trace_id in recorder.traces(shop_id) for span in recorder.spans(trace_id, shop_id)]
    grounded = [span for span in spans if span.kind == "retrieval"]
    cited = [span for span in grounded if span.attributes.get("citation_page") is not None]
    latencies = sorted(span.latency_ms for span in spans)
    return {
        "trace_count": len(recorder.traces(shop_id)),
        "span_count": len(spans),
        "spans_by_kind": {
            kind: sum(1 for span in spans if span.kind == kind) for kind in SPAN_KINDS
        },
        "citation_rate": (len(cited) / len(grounded)) if grounded else 0.0,
        "p50_latency_ms": _percentile(latencies, 0.50),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "total_cost_mxn": str(sum((span.cost_mxn for span in spans), Decimal("0.0000"))),
        "escalation_outcomes": escalation_outcomes,
        "evaluation_thresholds_met": evaluation_thresholds_met,
        "evaluation_score": evaluation_score,
    }


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    index = min(round((len(values) - 1) * fraction), len(values) - 1)
    return values[index]
