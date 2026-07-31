"""The validator reads SQL as a parsed statement, not as text."""

import pytest

from service_advisor_api.text_to_sql import (
    ROW_LIMIT,
    SemanticQueryGateway,
    UnsafeSqlError,
    validate_sql,
)


@pytest.fixture
def gateway() -> SemanticQueryGateway:
    store = SemanticQueryGateway()
    store.seed()
    return store


@pytest.mark.parametrize(
    "attack",
    [
        'SELECT customer_name FROM v_service_history, "base_customers"',
        "SELECT service_code FROM v_service_history CROSS JOIN base_customers",
        "SELECT service_code FROM v_service_history JOIN base_quotes ON 1 = 1",
        "SELECT vehicle_id FROM (SELECT * FROM base_customers)",
        "SELECT vehicle_id FROM v_service_history WHERE vehicle_id IN (SELECT vehicle_id FROM base_customers)",
        "WITH leak AS (SELECT * FROM base_customers) SELECT * FROM leak",
        "SELECT service_code FROM v_service_history UNION SELECT customer_name FROM base_customers",
        "SELECT b.customer_name FROM v_service_history, base_customers AS b",
        "SELECT service_code FROM main.base_customers",
        "SELECT name FROM sqlite_master",
        "DELETE FROM v_service_history",
        "SELECT service_code FROM v_service_history; DROP TABLE base_quotes",
    ],
    ids=[
        "quoted-base-table", "cross-join", "explicit-join", "subquery-source",
        "where-in-subquery", "cte", "union", "aliased-base-table", "schema-qualified",
        "system-catalog", "mutation", "stacked-statement",
    ],
)
def test_the_parser_sees_through_every_disguise(attack: str) -> None:
    """What if the base table is reached by a shape the regex never enumerated?"""
    with pytest.raises(UnsafeSqlError):
        validate_sql(attack)


def test_a_correctly_quoted_view_is_legitimate() -> None:
    """What if the caller quotes an allowlisted view instead of writing it bare?

    The blunt quote ban was a regex workaround; the parser resolves the identifier.
    """
    accepted = validate_sql('SELECT "service_code" FROM "v_service_history"')

    assert accepted.views == ("v_service_history",)
    assert accepted.columns == ("service_code",)


def test_an_unallowlisted_column_is_refused_even_on_an_allowed_view() -> None:
    with pytest.raises(UnsafeSqlError, match="column"):
        validate_sql("SELECT customer_name FROM v_service_history")


def test_an_unsafe_function_is_refused() -> None:
    with pytest.raises(UnsafeSqlError, match="function"):
        validate_sql("SELECT load_extension('evil') FROM v_service_history")


def test_an_allowlisted_aggregate_is_accepted() -> None:
    accepted = validate_sql(
        "SELECT service_code, count(*) FROM v_service_history GROUP BY service_code"
    )

    assert accepted.views == ("v_service_history",)


def test_a_multi_view_read_is_still_allowed() -> None:
    accepted = validate_sql(
        "SELECT vehicle_id FROM v_service_history, v_parts_availability"
    )

    assert set(accepted.views) == {"v_service_history", "v_parts_availability"}


def test_restating_the_tenant_filter_is_refused() -> None:
    with pytest.raises(UnsafeSqlError, match="[Tt]enant"):
        validate_sql("SELECT service_code FROM v_service_history WHERE shop_id = 'other-shop'")


@pytest.mark.parametrize(
    ("sql", "expected_rows"),
    [
        ("SELECT recorded_on FROM v_service_history", 2),
        ("SELECT recorded_on FROM v_service_history LIMIT 1", 1),
        ("SELECT recorded_on FROM v_service_history LIMIT 1 OFFSET 1", 1),
        ("SELECT recorded_on FROM v_service_history LIMIT 1,1", 1),
        ("SELECT recorded_on FROM v_service_history LIMIT 5000", 2),
    ],
    ids=["no-limit", "limit", "limit-offset", "comma-limit", "over-cap"],
)
def test_the_regenerated_query_runs_and_respects_the_cap(
    gateway: SemanticQueryGateway, sql: str, expected_rows: int
) -> None:
    """What if the limit is rewritten by string surgery instead of by the parser?"""
    accepted = validate_sql(sql)

    rows = gateway.execute(accepted, "demo-shop")

    assert len(rows) == expected_rows
    assert accepted.row_limit <= ROW_LIMIT


def test_an_offset_still_selects_the_later_row(gateway: SemanticQueryGateway) -> None:
    every = gateway.execute(validate_sql("SELECT recorded_on FROM v_service_history"), "demo-shop")

    offset = gateway.execute(
        validate_sql("SELECT recorded_on FROM v_service_history LIMIT 1 OFFSET 1"), "demo-shop"
    )

    assert offset == (every[1],)


def test_the_executed_sql_is_the_parsers_own_output() -> None:
    accepted = validate_sql("select   service_code   from v_service_history")

    assert accepted.sql == "SELECT service_code FROM v_service_history LIMIT 100"


def test_malformed_sql_is_refused_before_it_reaches_the_database() -> None:
    with pytest.raises(UnsafeSqlError):
        validate_sql("SELECT FROM WHERE")


def test_the_principal_rechecks_a_forged_query(gateway: SemanticQueryGateway) -> None:
    """What if validation is bypassed entirely and execute() is handed raw SQL?"""
    accepted = validate_sql("SELECT service_code FROM v_service_history")
    forged = type(accepted)(
        sql="SELECT customer_name FROM base_customers LIMIT 1",
        views=accepted.views,
        columns=accepted.columns,
        row_limit=1,
        timeout_seconds=accepted.timeout_seconds,
        principal=accepted.principal,
    )

    with pytest.raises(UnsafeSqlError):
        gateway.execute(forged, "demo-shop")
