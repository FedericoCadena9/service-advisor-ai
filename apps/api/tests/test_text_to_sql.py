import pytest

from service_advisor_api.text_to_sql import (
    ROW_LIMIT,
    SemanticQueryGateway,
    UnsafeSqlError,
    UnsupportedQuestionError,
    generate_sql,
    validate_sql,
)

ATTACKS = {
    "mutation": "DELETE FROM v_service_history",
    "disguised_mutation": "SELECT * FROM v_service_history; DROP TABLE base_quotes",
    "comment": "SELECT service_code FROM v_service_history -- WHERE status = 'declined'",
    "block_comment": "SELECT service_code /* hidden */ FROM v_service_history",
    "multi_statement": "SELECT service_code FROM v_service_history; SELECT 1",
    "base_table": "SELECT customer_name FROM base_customers",
    "system_catalog": "SELECT name FROM sqlite_master",
    "unsafe_function": "SELECT load_extension('evil') FROM v_service_history",
    "tenant_bypass": "SELECT service_code FROM v_service_history WHERE shop_id = 'other-shop'",
    "hidden_column": "SELECT phone FROM v_service_history",
    "malformed": "SELECT FROM WHERE",
    "not_a_select": "WITH x AS (SELECT 1) SELECT * FROM x",
}


@pytest.fixture
def gateway() -> SemanticQueryGateway:
    store = SemanticQueryGateway()
    store.seed()
    return store


@pytest.mark.parametrize("attack", sorted(ATTACKS), ids=sorted(ATTACKS))
def test_every_unsafe_query_is_blocked(attack: str) -> None:
    with pytest.raises(UnsafeSqlError):
        validate_sql(ATTACKS[attack])


def test_accepted_query_forces_a_row_limit() -> None:
    accepted = validate_sql("SELECT service_code FROM v_service_history")

    assert accepted.sql.endswith(f"LIMIT {ROW_LIMIT}")
    assert accepted.row_limit == ROW_LIMIT
    assert accepted.views == ("v_service_history",)
    assert accepted.columns == ("service_code",)
    assert accepted.principal == "semantic_reader"
    assert accepted.timeout_seconds == 2.0


def test_a_larger_user_limit_is_clamped() -> None:
    assert validate_sql("SELECT service_code FROM v_service_history LIMIT 5000").row_limit == 100


def test_rows_are_filtered_to_the_calling_tenant(gateway: SemanticQueryGateway) -> None:
    accepted = validate_sql("SELECT part_number, on_hand FROM v_parts_availability")

    demo_rows = gateway.execute(accepted, "demo-shop")
    other_rows = gateway.execute(accepted, "other-shop")

    assert demo_rows == (("HON-OIL-0W20", 12), ("HON-CABIN-80292", 0))
    assert other_rows == (("HON-OIL-0W20", 3),)


def test_the_principal_refuses_personal_data_in_base_tables(gateway: SemanticQueryGateway) -> None:
    accepted = validate_sql("SELECT vehicle_id FROM v_service_history")
    personal = type(accepted)(
        sql="SELECT customer_name FROM base_customers LIMIT 1",
        views=accepted.views,
        columns=accepted.columns,
        row_limit=1,
        timeout_seconds=accepted.timeout_seconds,
        principal=accepted.principal,
    )

    with pytest.raises(UnsafeSqlError):
        gateway.execute(personal, "demo-shop")


def test_writes_fail_even_if_validation_is_bypassed(gateway: SemanticQueryGateway) -> None:
    accepted = validate_sql("SELECT service_code FROM v_service_history")
    write = type(accepted)(
        sql="DELETE FROM base_quotes",
        views=accepted.views,
        columns=accepted.columns,
        row_limit=accepted.row_limit,
        timeout_seconds=accepted.timeout_seconds,
        principal=accepted.principal,
    )

    with pytest.raises(UnsafeSqlError):
        gateway.execute(write, "demo-shop")


def test_supported_question_answers_from_one_query(gateway: SemanticQueryGateway) -> None:
    result = gateway.run("How many services were declined?", "demo-shop")

    assert result.answer == "Declined services: HONDA-A1 1."
    assert result.query.views == ("v_service_history",)
    assert result.rows == (("HONDA-A1", 1),)


def test_unsupported_question_is_refused(gateway: SemanticQueryGateway) -> None:
    with pytest.raises(UnsupportedQuestionError):
        gateway.run("What is the customer phone number?", "demo-shop")


def test_generated_sql_is_always_validated() -> None:
    sql, topic = generate_sql("Which parts are on backorder?")

    assert topic == "parts availability"
    assert validate_sql(sql).views == ("v_parts_availability",)
