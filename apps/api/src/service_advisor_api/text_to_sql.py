import sqlite3
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DIALECT = "sqlite"
TENANT_COLUMN = "shop_id"
ROW_LIMIT = 100
TIMEOUT_SECONDS = 2.0
PRINCIPAL = "semantic_reader"

ALLOWED_VIEWS = {
    "v_service_history": ("vehicle_id", "service_code", "status", "recorded_on"),
    "v_parts_availability": ("part_number", "on_hand", "restock_status"),
    "v_quote_totals": ("quote_id", "vehicle_id", "total_mxn", "approver_role"),
}
ALLOWED_FUNCTIONS = {"count", "sum", "avg", "min", "max", "round"}
# A derived table hides its source behind a projection, so the FROM list must name views.
_DERIVED_SOURCES = (exp.Subquery, exp.Union, exp.Lateral)


class UnsafeSqlError(ValueError):
    """Raised when generated SQL leaves the agreed read-only, tenant-scoped envelope."""


class UnsupportedQuestionError(ValueError):
    """Raised when a question has no supported semantic query."""


class QueryFailedError(RuntimeError):
    """Raised when an accepted query is malformed: a caller error, not a security refusal."""


class QueryTimeoutError(RuntimeError):
    """Raised when a query exceeds the strict timeout."""


@dataclass(frozen=True)
class AcceptedQuery:
    sql: str
    views: tuple[str, ...]
    columns: tuple[str, ...]
    row_limit: int
    timeout_seconds: float
    principal: str


@dataclass(frozen=True)
class QueryResult:
    answer: str
    rows: tuple[tuple[Any, ...], ...]
    query: AcceptedQuery


SUPPORTED_QUESTIONS = (
    (
        ("declin",),
        (
            "SELECT service_code, count(*) FROM v_service_history WHERE status = 'declined' "
            "GROUP BY service_code"
        ),
        "declined services",
    ),
    (
        ("part", "backorder", "stock"),
        (
            "SELECT part_number, on_hand, restock_status FROM v_parts_availability "
            "ORDER BY part_number"
        ),
        "parts availability",
    ),
    (
        ("quote", "approved", "total"),
        "SELECT quote_id, total_mxn, approver_role FROM v_quote_totals ORDER BY quote_id",
        "approved quote totals",
    ),
)


def generate_sql(question: str) -> tuple[str, str]:
    normalized = question.lower()
    for keywords, sql, topic in SUPPORTED_QUESTIONS:
        if any(keyword in normalized for keyword in keywords):
            return sql, topic
    raise UnsupportedQuestionError("No supported semantic query answers this question")


def validate_sql(sql: str) -> AcceptedQuery:
    """Accept one read-only SELECT over allowlisted semantic views, with a forced row limit.

    The statement is parsed, inspected as a tree, and re-rendered from that tree. Reading
    structure rather than text is what makes a disguise -- a comma join, a quoted
    identifier, a nested subquery, an alias -- indistinguishable from the plain form.
    """
    if "--" in sql or "/*" in sql:
        raise UnsafeSqlError("SQL comments are not allowed")
    try:
        statements = [statement for statement in sqlglot.parse(sql, read=DIALECT) if statement]
    except ParseError as error:
        raise UnsafeSqlError(f"The query could not be parsed: {error}") from error
    if len(statements) != 1:
        raise UnsafeSqlError("Only a single statement is allowed")

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise UnsafeSqlError("Only a single SELECT statement is allowed")
    if statement.args.get("with"):
        raise UnsafeSqlError("Common table expressions are not allowed")
    if any(next(statement.find_all(node_type), None) for node_type in _DERIVED_SOURCES):
        raise UnsafeSqlError("Only allowlisted semantic views may be read")

    views = _referenced_views(statement)
    columns = _referenced_columns(statement, views)
    _reject_unsafe_functions(statement)

    row_limit, offset = _row_window(statement)
    statement.set("limit", exp.Limit(expression=exp.Literal.number(row_limit)))
    if offset:
        statement.set("offset", exp.Offset(expression=exp.Literal.number(offset)))
    return AcceptedQuery(
        sql=statement.sql(dialect=DIALECT),
        views=views,
        columns=columns,
        row_limit=row_limit,
        timeout_seconds=TIMEOUT_SECONDS,
        principal=PRINCIPAL,
    )


def _referenced_views(statement: exp.Select) -> tuple[str, ...]:
    """Every table the statement reads, however it was written."""
    views: list[str] = []
    for table in statement.find_all(exp.Table):
        if table.db or table.catalog:
            raise UnsafeSqlError("Schema-qualified tables are not readable")
        name = table.name.lower()
        if name not in ALLOWED_VIEWS:
            raise UnsafeSqlError(f"{name} is not an allowlisted semantic view")
        if name not in views:
            views.append(name)
    if not views:
        raise UnsafeSqlError("The query must read an allowlisted semantic view")
    return tuple(views)


def _referenced_columns(statement: exp.Select, views: tuple[str, ...]) -> tuple[str, ...]:
    allowed = {column for view in views for column in ALLOWED_VIEWS[view]}
    referenced: list[str] = []
    for column in statement.find_all(exp.Column):
        name = column.name.lower()
        if name == TENANT_COLUMN:
            raise UnsafeSqlError(
                "Tenant filtering is applied by the gateway and cannot be restated"
            )
        if name not in allowed:
            raise UnsafeSqlError(f"{name} is not an allowlisted column")
        if name not in referenced:
            referenced.append(name)
    return tuple(referenced)


def _reject_unsafe_functions(statement: exp.Select) -> None:
    for function in statement.find_all(exp.Func):
        name = (
            function.this if isinstance(function, exp.Anonymous) else function.sql_name()
        )
        if str(name).lower() not in ALLOWED_FUNCTIONS:
            raise UnsafeSqlError(f"{str(name).lower()} is not an allowlisted function")


def _row_window(statement: exp.Select) -> tuple[int, int]:
    """Read the caller's window, capping the count and keeping the offset intact."""
    limit = statement.args.get("limit")
    offset = statement.args.get("offset")
    requested = int(limit.expression.name) if limit is not None else ROW_LIMIT
    skipped = int(offset.expression.name) if offset is not None else 0
    return min(requested, ROW_LIMIT), skipped


class SemanticQueryGateway:
    """A read-only principal over tenant-filtered semantic views."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._shop_id = ""
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.create_function("current_shop", 0, lambda: self._shop_id)
        self._create_schema()
        self._connection.execute("PRAGMA query_only = ON")

    def run(self, question: str, shop_id: str) -> QueryResult:
        sql, topic = generate_sql(question)
        query = validate_sql(sql)
        rows = self.execute(query, shop_id)
        return QueryResult(answer=_render_answer(topic, rows), rows=rows, query=query)

    def execute(self, query: AcceptedQuery, shop_id: str) -> tuple[tuple[Any, ...], ...]:
        # Defence in depth: the principal re-parses the envelope it was handed, so a
        # compromised caller cannot hand execute() something validate_sql never saw.
        try:
            statement = sqlglot.parse_one(query.sql, read=DIALECT)
        except ParseError as error:
            raise UnsafeSqlError(f"{PRINCIPAL} cannot parse this query") from error
        if not isinstance(statement, exp.Select):
            raise UnsafeSqlError(f"{PRINCIPAL} may only read")
        for table in statement.find_all(exp.Table):
            if table.name.lower() not in ALLOWED_VIEWS:
                raise UnsafeSqlError(f"{table.name.lower()} is not readable by {PRINCIPAL}")
        deadline = time.monotonic() + query.timeout_seconds
        with self._lock:
            self._shop_id = shop_id
            self._connection.set_progress_handler(
                lambda: 1 if time.monotonic() > deadline else 0, 1_000
            )
            try:
                return tuple(self._connection.execute(query.sql).fetchall())
            except sqlite3.OperationalError as error:
                if "interrupted" in str(error):
                    raise QueryTimeoutError("The query exceeded the strict timeout") from error
                raise QueryFailedError(str(error)) from error
            finally:
                self._connection.set_progress_handler(None, 0)
                self._shop_id = ""

    def _create_schema(self) -> None:
        # Base tables keep personal data; semantic views expose neither names nor contact details.
        self._connection.executescript(
            """
            CREATE TABLE base_customers (
                shop_id TEXT, vehicle_id TEXT, customer_name TEXT, phone TEXT
            );
            CREATE TABLE base_service_records (
                shop_id TEXT, vehicle_id TEXT, service_code TEXT, status TEXT, recorded_on TEXT
            );
            CREATE TABLE base_parts_inventory (
                shop_id TEXT, part_number TEXT, on_hand INTEGER, restock_status TEXT
            );
            CREATE TABLE base_quotes (
                shop_id TEXT, quote_id TEXT, vehicle_id TEXT, total_mxn TEXT, approver_role TEXT
            );
            CREATE VIEW v_service_history AS
                SELECT vehicle_id, service_code, status, recorded_on
                FROM base_service_records WHERE shop_id = current_shop();
            CREATE VIEW v_parts_availability AS
                SELECT part_number, on_hand, restock_status
                FROM base_parts_inventory WHERE shop_id = current_shop();
            CREATE VIEW v_quote_totals AS
                SELECT quote_id, vehicle_id, total_mxn, approver_role
                FROM base_quotes WHERE shop_id = current_shop();
            """
        )
        self._connection.commit()

    def seed(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA query_only = OFF")
            self._connection.executemany(
                "INSERT INTO base_customers VALUES (?, ?, ?, ?)",
                (
                    ("demo-shop", "honda-civic-2019-lx", "Demo Customer", "+52 55 0000 0000"),
                    ("other-shop", "honda-crv-2021-ex", "Otro Cliente", "+52 55 1111 1111"),
                ),
            )
            self._connection.executemany(
                "INSERT INTO base_service_records VALUES (?, ?, ?, ?, ?)",
                (
                    ("demo-shop", "honda-civic-2019-lx", "HONDA-A1", "completed", "2026-05-10"),
                    ("demo-shop", "honda-civic-2019-lx", "HONDA-A1", "declined", "2026-06-18"),
                    ("other-shop", "honda-crv-2021-ex", "HONDA-B1", "declined", "2026-06-20"),
                ),
            )
            self._connection.executemany(
                "INSERT INTO base_parts_inventory VALUES (?, ?, ?, ?)",
                (
                    ("demo-shop", "HON-OIL-0W20", 12, "in_stock"),
                    ("demo-shop", "HON-CABIN-80292", 0, "backordered"),
                    ("other-shop", "HON-OIL-0W20", 3, "in_stock"),
                ),
            )
            self._connection.executemany(
                "INSERT INTO base_quotes VALUES (?, ?, ?, ?, ?)",
                (
                    ("demo-shop", "quote-demo-1", "honda-civic-2019-lx", "1847.88", "advisor"),
                    ("other-shop", "quote-other-1", "honda-crv-2021-ex", "9200.00", "manager"),
                ),
            )
            self._connection.commit()
            self._connection.execute("PRAGMA query_only = ON")


def _render_answer(topic: str, rows: tuple[tuple[Any, ...], ...]) -> str:
    if not rows:
        return f"No {topic} are recorded for this shop."
    rendered = "; ".join(" ".join(str(value) for value in row) for row in rows)
    return f"{topic.capitalize()}: {rendered}."
