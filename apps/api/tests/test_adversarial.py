"""Adversarial regressions: every case here was a working bypass before the fix."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from test_approvals import CITATIONS, FACTS, NO_ESCALATION

from service_advisor_api.approvals import (
    QuoteCommandStore,
    QuoteFacts,
    StaleQuoteError,
)
from service_advisor_api.evaluation import UNSAFE_SQL_ATTACKS, build_corpus, run_suite
from service_advisor_api.messaging import (
    OPTIONAL_CLAUSES,
    InventedContentError,
    MessageAlreadySentError,
    MessagingStore,
    compose_sms,
    validate_sms,
)
from service_advisor_api.observability import REDACTED, redact_attributes
from service_advisor_api.operations import PartAvailability
from service_advisor_api.quotes import draft_quote
from service_advisor_api.text_to_sql import (
    QueryFailedError,
    SemanticQueryGateway,
    UnsafeSqlError,
    validate_sql,
)

APPROVED_SMS = {
    "customer_label": "Demo Customer",
    "service_codes": ("HONDA-A1",),
    "total_mxn": Decimal("1847.88"),
    "slot_label": "2026-08-03T09:00:00",
}


def test_main_only_composes_the_feature_routers() -> None:
    """What if a future endpoint is added to main instead of its feature router?"""
    import ast
    from pathlib import Path

    source = ast.parse(
        Path(__file__).resolve().parents[1].joinpath("src/service_advisor_api/main.py").read_text()
    )
    registrations = {
        call.args[0].value.id
        for call in ast.walk(source)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "include_router"
        and call.args
        and isinstance(call.args[0], ast.Attribute)
        and isinstance(call.args[0].value, ast.Name)
    }
    app_routes = [
        decorator
        for node in source.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "app"
    ]

    assert registrations == {
        "admin",
        "appointments",
        "health",
        "insights",
        "quotes",
        "runs",
        "sessions",
        "vehicles",
        "voice",
    }
    assert app_routes == []


# 1. Text-to-SQL


@pytest.mark.parametrize(
    "attack",
    [
        'SELECT "customer_name", "phone" FROM v_service_history, "base_customers"',
        'SELECT "total_mxn" FROM v_service_history, "base_quotes"',
        "SELECT service_code FROM v_service_history, base_customers",
        "SELECT name FROM v_service_history, pragma_table_list",
    ],
    ids=["quoted-comma-join", "quoted-quotes-table", "bare-comma-join", "pragma-function"],
)
def test_quoted_identifiers_and_comma_joins_are_blocked(attack: str) -> None:
    """What if the attacker comma-joins a quoted base table instead of using JOIN?

    Quoting an allowlisted view is legitimate and is covered in test_sql_ast.py; what must
    stay blocked is the table the quotes were hiding.
    """
    with pytest.raises(UnsafeSqlError):
        validate_sql(attack)


def test_the_gateway_never_returns_another_tenants_rows() -> None:
    gateway = SemanticQueryGateway()
    gateway.seed()

    with pytest.raises(UnsafeSqlError):
        gateway.execute(
            validate_sql("SELECT service_code FROM v_service_history"),
            "demo-shop",
        ) and validate_sql('SELECT "phone" FROM v_service_history, "base_customers"')


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT service_code FROM v_service_history LIMIT 0,5",
        "SELECT service_code FROM v_service_history LIMIT 5 OFFSET 2",
    ],
    ids=["comma-limit", "offset-limit"],
)
def test_limit_variants_are_handled_without_a_broken_query(sql: str) -> None:
    """What if the caller writes LIMIT 0,5 instead of LIMIT 5?"""
    accepted = validate_sql(sql)

    assert accepted.row_limit <= 100
    assert accepted.sql.count("LIMIT") == 1


# 2. Messaging


@pytest.mark.parametrize(
    "text",
    [
        (
            "Hola Demo Customer: su servicio incluye cambio de aceite y filtro. "
            "Total $5000 MXN. Cita 2026-08-03T09:00:00. ¿Confirma la cita?"
        ),
        "Hola Demo Customer: son doce mil pesos. Cita 2026-08-03T09:00:00. ¿Confirma la cita?",
        (
            "Hola Demo Customer y tambien Luis Ramirez: su servicio incluye cambio de aceite "
            "y filtro. Total $1,847.88 MXN con IVA incluido. Cita 2026-08-03T09:00:00. "
            "¿Confirma la cita?"
        ),
        (
            "Hola Demo Customer: su servicio incluye transmision, suspension, clutch, bujias "
            "y amortiguadores. Total $1,847.88 MXN con IVA incluido. "
            "Cita 2026-08-03T09:00:00. ¿Confirma la cita?"
        ),
        (
            "Hola Demo Customer: atienda de inmediato o puede quedarse tirado. "
            "Total $1,847.88 MXN con IVA incluido. Cita 2026-08-03T09:00:00. ¿Confirma la cita?"
        ),
        (
            "Hola Demo Customer: es URGENTÉ. Total $1,847.88 MXN con IVA incluido. "
            "Cita 2026-08-03T09:00:00. ¿Confirma la cita?"
        ),
    ],
    ids=["integer-price", "price-in-words", "extra-recipient", "invented-services", "urgency-prose", "accented-urgency"],
)
def test_invented_message_content_is_rejected(text: str) -> None:
    """What if the Advisor writes prose instead of editing the approved preview?"""
    with pytest.raises(InventedContentError):
        validate_sms(text, **APPROVED_SMS)


def test_the_approved_preview_and_a_shortened_edit_still_pass() -> None:
    preview = compose_sms(**APPROVED_SMS)
    shortened = (
        "Hola Demo Customer: su servicio incluye cambio de aceite y filtro. "
        "Total $1,847.88 MXN con IVA incluido. Cita 2026-08-03T09:00:00. ¿Confirma la cita?"
    )

    assert validate_sms(preview.text, **APPROVED_SMS) >= 1
    assert validate_sms(shortened, **APPROVED_SMS) >= 1


# 3 and 7. Approval lifecycle


def _store_with_review(now: datetime | None = None) -> tuple[QuoteCommandStore, str]:
    store = QuoteCommandStore()
    review = store.open_review(
        shop_id="demo-shop",
        demo_session_id="session-1",
        vehicle_id="honda-civic-2019-lx",
        facts=FACTS,
        citations=CITATIONS,
        fingerprint="fingerprint-a",
        now=now,
    )
    return store, review.id


def _reject(store: QuoteCommandStore, review_id: str):
    return store.reject(
        review_id,
        shop_id="demo-shop",
        demo_session_id="session-1",
        approver_role="advisor",
        approver_session_id="session-1",
        reason="Customer declined",
    )


def _approve(store: QuoteCommandStore, review_id: str, **overrides):
    arguments = {
        "shop_id": "demo-shop",
        "demo_session_id": "session-1",
        "approver_role": "advisor",
        "approver_session_id": "session-1",
        "idempotency_key": "key-1",
        "current_facts": FACTS,
        "current_fingerprint": "fingerprint-a",
        "escalation": NO_ESCALATION,
    }
    return store.approve(review_id, **{**arguments, **overrides})


def test_a_rejected_quote_cannot_be_resurrected_by_a_price_change() -> None:
    """What if inventory moves after a rejection instead of before it?"""
    store, review_id = _store_with_review()
    _reject(store, review_id)

    store.revalidate(review_id, FACTS, "fingerprint-b")

    with pytest.raises(StaleQuoteError):
        _approve(store, review_id, current_fingerprint="fingerprint-b")


def test_an_invalidated_approval_can_still_be_rejected() -> None:
    """What if the customer declines after the quote returned to review?"""
    store, review_id = _store_with_review()
    _approve(store, review_id)
    store.revalidate(review_id, QuoteFacts(**FACTS.__dict__), "fingerprint-b")

    rejection = _reject(store, review_id)

    assert rejection.decision == "rejected"
    assert rejection.quote_id is None


def test_the_idempotency_key_decides_the_saved_quote() -> None:
    """What if the same key is replayed after the quote was reopened and re-approved?"""
    store, review_id = _store_with_review()
    first = _approve(store, review_id, idempotency_key="key-1")

    replay = _approve(store, review_id, idempotency_key="key-1")

    assert replay.id == first.id


def test_a_naive_expiry_clock_is_still_comparable() -> None:
    """What if a caller passes a naive datetime instead of an aware one?"""
    store, review_id = _store_with_review(now=datetime(2026, 7, 31, 12, 0))  # noqa: DTZ001

    decision = _approve(store, review_id, now=datetime(2026, 7, 31, 13, 0, tzinfo=UTC))

    assert decision.decision == "approved"


# 4. Redaction


def test_redaction_reaches_nested_structures() -> None:
    """What if the personal data sits one dict deeper instead of at the top level?"""
    payload = redact_attributes(
        {
            "nested": {"phone": "+52 55 1234 5678", "customer_name": "Ana Lopez"},
            "note": ["call +52 55 0000 0000", "mail ana@example.com"],
            "citation_page": 42,
        }
    )

    rendered = str(payload)
    assert "Ana Lopez" not in rendered
    assert "+52 55 1234 5678" not in rendered
    assert "ana@example.com" not in rendered
    assert REDACTED in rendered
    assert "nested" not in payload
    assert payload["citation_page"] == 42


# 5. Parts consumption


def test_a_shared_consumable_is_stocked_for_the_whole_bundle() -> None:
    """What if the bundle needs six litres while only five are on hand?"""
    draft = draft_quote(
        ["FORD-SCHED-D", "FORD-SCHED-E"],
        engine="2.3L",
        parts={"FOR-OIL-5W30": PartAvailability("FOR-OIL-5W30", 5, "in_stock", None)},
        slots=(),
    )

    assert all(not line.available for line in draft.lines)
    assert draft.lines[0].unavailable_reason == (
        "Part FOR-OIL-5W30 has 5 of 6 required in stock"
    )
    assert draft.total_mxn == Decimal("0.00")


def test_a_shared_consumable_is_charged_once_and_reserved_once() -> None:
    """What if both services fit the same oil change instead of two separate ones?"""
    draft = draft_quote(
        ["FORD-SCHED-D", "FORD-SCHED-E"],
        engine="2.3L",
        parts={"FOR-OIL-5W30": PartAvailability("FOR-OIL-5W30", 6, "in_stock", None)},
        slots=(),
    )

    first, second = draft.lines
    assert first.parts_mxn == Decimal("1308.00")
    assert second.parts_mxn == Decimal("0.00")
    assert second.labor_mxn == Decimal("0.00")
    assert draft.duration_minutes == 50


# 6. Evaluation honesty


def test_every_recorded_attack_is_exercised() -> None:
    """What if an attack sits in the list but no case ever runs it?"""
    corpus = [case for case in build_corpus() if case.archetype == "unsafe_sql"]

    report = run_suite(corpus)

    assert report.scores["unsafe_sql"] == 1.0
    assert report.attacks_exercised == len(UNSAFE_SQL_ATTACKS)


def test_the_provider_label_matches_the_results_that_were_run() -> None:
    """What if a live run is labelled deterministic instead of live?"""
    corpus = build_corpus()

    report = run_suite(corpus, live_model=lambda case: True, provider="deterministic")

    assert report.provider == "live_model"


# Second round: regressions the fixes themselves introduced.


@pytest.mark.parametrize(
    "suffix",
    [
        " total $99,999.00",
        " 🚨🚨🚨",
        " 55-1234-5678",
        " total $99,999.00 🚨 55-1234-5678",
        " 55.1234.5678 / 99.99",
    ],
    ids=["second-price", "emoji-urgency", "phone-number", "all-three", "punctuated-digits"],
)
def test_numbers_and_symbols_cannot_be_smuggled_past_the_word_allowlist(suffix: str) -> None:
    """What if the invented content is digits or emoji instead of words?"""
    approved = compose_sms(**APPROVED_SMS).text

    with pytest.raises(InventedContentError):
        validate_sms(approved + suffix, **APPROVED_SMS)


def test_repeating_an_approved_label_cannot_exceed_the_priority_cap() -> None:
    """What if one approved label is repeated eight times instead of three listed once?"""
    approved = compose_sms(**APPROVED_SMS).text
    padded = approved + " cambio de aceite y filtro" * 8

    with pytest.raises(InventedContentError):
        validate_sms(padded, **APPROVED_SMS)


def test_an_offset_is_honoured_instead_of_silently_dropped() -> None:
    """What if the caller asks for the second row instead of the first?"""
    gateway = SemanticQueryGateway()
    gateway.seed()
    all_rows = gateway.execute(
        validate_sql("SELECT recorded_on FROM v_service_history"), "demo-shop"
    )

    offset_rows = gateway.execute(
        validate_sql("SELECT recorded_on FROM v_service_history LIMIT 1 OFFSET 1"), "demo-shop"
    )
    comma_rows = gateway.execute(
        validate_sql("SELECT recorded_on FROM v_service_history LIMIT 1,1"), "demo-shop"
    )

    assert offset_rows == (all_rows[1],)
    assert comma_rows == (all_rows[1],)


def test_a_parenthesised_from_entry_is_refused() -> None:
    """What if the FROM list holds a subquery instead of a view name?"""
    with pytest.raises(UnsafeSqlError):
        validate_sql("SELECT vehicle_id FROM v_service_history, (SELECT 1)")


def test_an_unlisted_attribute_key_cannot_carry_personal_data() -> None:
    """What if the personal data arrives under a key nobody put on the denylist?"""
    payload = redact_attributes(
        {
            "caller": "Ana Lopez Martinez",
            "address": "Av. Reforma 222, Cuauhtemoc, CDMX",
            "citation_page": 42,
        }
    )

    assert payload == {"citation_page": 42}


def test_a_short_local_phone_number_is_still_scrubbed() -> None:
    payload = redact_attributes({"note": "owner reached at 1234567"})

    assert "1234567" not in str(payload)


def test_a_replayed_idempotency_key_returns_the_stored_decision() -> None:
    """What if the key map is the only thing that remembers the decision?"""
    store, review_id = _store_with_review()
    first = _approve(store, review_id, idempotency_key="key-1")
    store._decisions.clear()

    replay = _approve(store, review_id, idempotency_key="key-1")

    assert replay.id == first.id
    assert replay.quote_id == first.quote_id


# Third round: what the second-round fixes themselves broke.


def test_a_replayed_key_never_returns_a_superseded_approval() -> None:
    """What if the key is replayed after the price moved and a new quote was approved?"""
    store, review_id = _store_with_review()
    superseded = _approve(store, review_id, idempotency_key="key-a")
    repriced = QuoteFacts(**{**FACTS.__dict__, "total_mxn": Decimal("10440.00")})
    store.revalidate(review_id, repriced, "fingerprint-b")
    current = _approve(
        store,
        review_id,
        idempotency_key="key-b",
        current_facts=repriced,
        current_fingerprint="fingerprint-b",
    )

    replay = _approve(store, review_id, idempotency_key="key-a", current_fingerprint="fingerprint-b")

    assert replay.quote_id != superseded.quote_id
    assert replay.quote_id == current.quote_id
    assert replay.facts.total_mxn == Decimal("10440.00")
    assert store.get(review_id, shop_id="demo-shop", demo_session_id="session-1").status == (
        "approved"
    )


def test_an_unknown_replayed_key_does_not_crash() -> None:
    """What if the key map points at a decision the audit no longer holds?"""
    store, review_id = _store_with_review()
    _approve(store, review_id, idempotency_key="key-a")
    store._idempotency[(review_id, "key-a")] = "missing-decision"

    replay = _approve(store, review_id, idempotency_key="key-a")

    assert replay.quote_id is not None


def test_a_caret_cannot_be_appended_to_an_approved_message() -> None:
    """What if the edit is a symbol the character class let through by accident?"""
    approved = compose_sms(**APPROVED_SMS).text

    with pytest.raises(InventedContentError):
        validate_sms(approved + " ^^^^^^", **APPROVED_SMS)


def test_an_ordinary_spanish_courtesy_edit_is_allowed() -> None:
    """What if the Advisor adds a normal closing line instead of inventing facts?"""
    approved = compose_sms(**APPROVED_SMS).text

    for edit in (
        " Gracias por su preferencia.",
        " Si necesita cambiar la cita, responda a este mensaje.",
        " Su taller de confianza.",
    ):
        assert validate_sms(approved + edit, **APPROVED_SMS) >= 1


@pytest.mark.parametrize(
    "edit",
    [
        " Es urgente.",
        " Revise los frenos.",
        " Su motor esta danado.",
    ],
    ids=["urgency", "invented-service", "invented-diagnosis"],
)
def test_a_wider_courtesy_vocabulary_still_refuses_meaning(edit: str) -> None:
    approved = compose_sms(**APPROVED_SMS).text

    with pytest.raises(InventedContentError):
        validate_sms(approved + edit, **APPROVED_SMS)


def test_a_malformed_query_is_not_reported_as_a_security_refusal() -> None:
    """What if the query is merely ambiguous instead of unsafe?"""
    gateway = SemanticQueryGateway()
    gateway.seed()

    with pytest.raises(QueryFailedError):
        gateway.execute(
            validate_sql("SELECT vehicle_id FROM v_service_history, v_quote_totals"),
            "demo-shop",
        )


def test_every_emitted_span_attribute_survives_the_allowlist() -> None:
    """What if a future span adds a key nobody put on the allowlist?"""
    import ast
    from pathlib import Path

    from service_advisor_api.observability import ALLOWED_ATTRIBUTES

    router_sources = [
        ast.parse(path.read_text())
        for path in Path(__file__).resolve().parents[1]
        .joinpath("src/service_advisor_api/routers")
        .glob("*.py")
    ]
    emitted = {
        key.value
        for source in router_sources
        for node in ast.walk(source)
        if isinstance(node, ast.keyword) and node.arg == "attributes"
        if isinstance(node.value, ast.Dict)
        for key in node.value.keys
        if isinstance(key, ast.Constant)
    }

    assert emitted
    assert emitted <= ALLOWED_ATTRIBUTES


# Fourth round: the widened word list composed claims out of approved words.


@pytest.mark.parametrize(
    "edit",
    [
        " El total necesita cambiar.",
        " Su servicio necesita cambiar.",
        " Su servicio necesita un taller de confianza.",
        " Este total necesita confirmar.",
        " Necesita cambiar la cita.",
        " Necesita cambiar la cita a un taller.",
        " Responda a este mensaje este dia.",
        " Responda este dia, estamos aqui.",
    ],
    ids=[
        "price-will-change", "service-needs-change", "invented-diagnosis", "total-not-final",
        "slot-directive", "move-to-another-shop", "same-day-deadline", "same-day-variant",
    ],
)
def test_approved_words_cannot_be_composed_into_new_claims(edit: str) -> None:
    """What if the claim is built only from words the vocabulary already allows?"""
    approved = compose_sms(**APPROVED_SMS).text

    with pytest.raises(InventedContentError):
        validate_sms(approved + edit, **APPROVED_SMS)


def test_the_approved_optional_clauses_are_still_writable() -> None:
    """What if the Advisor adds one of the offered closing lines?"""
    approved = compose_sms(**APPROVED_SMS).text

    for clause in OPTIONAL_CLAUSES:
        assert validate_sms(f"{approved} {clause}", **APPROVED_SMS) >= 1
    assert validate_sms(
        f"{approved} {OPTIONAL_CLAUSES[0]} {OPTIONAL_CLAUSES[1]}", **APPROVED_SMS
    ) >= 1


def test_a_clause_fragment_is_not_accepted() -> None:
    """What if only half of an approved clause is used, to change its meaning?"""
    approved = compose_sms(**APPROVED_SMS).text

    with pytest.raises(InventedContentError):
        validate_sms(f"{approved} Si necesita cambiar la cita.", **APPROVED_SMS)


def test_resending_a_different_message_for_one_quote_is_refused() -> None:
    """What if the second enqueue carries different text instead of a retry of the same?"""
    store = MessagingStore()
    enqueue = {
        "quote_id": "quote-1",
        "shop_id": "demo-shop",
        "demo_session_id": "session-1",
        "segments": 1,
        "approver_role": "advisor",
        "rule_version": "v1",
        "citation_page": 42,
        "citation_section": "Maintenance Minder",
    }
    first = store.enqueue(**enqueue, text="Hola Demo Customer: ¿Confirma la cita?")

    repeat = store.enqueue(**enqueue, text="Hola Demo Customer: ¿Confirma la cita?")
    with pytest.raises(MessageAlreadySentError):
        store.enqueue(**enqueue, text="Hola Demo Customer: otra cosa")

    assert repeat.id == first.id
