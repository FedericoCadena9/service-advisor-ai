import re
import sqlite3
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any

ROW_LIMIT = 100
TIMEOUT_SECONDS = 2.0
PRINCIPAL = "semantic_reader"

ALLOWED_VIEWS = {
    "v_service_history": ("vehicle_id", "service_code", "status", "recorded_on"),
    "v_parts_availability": ("part_number", "on_hand", "restock_status"),
    "v_quote_totals": ("quote_id", "vehicle_id", "total_mxn", "approver_role"),
}
ALLOWED_FUNCTIONS = {"count", "sum", "avg", "min", "max", "round"}
SQL_KEYWORDS = {
    "select", "from", "where", "group", "by", "order", "having", "limit", "as", "and", "or",
    "not", "in", "is", "null", "asc", "desc", "distinct", "on", "join", "inner", "left", "using",
    "offset",
}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace|"
    r"truncate|grant|revoke|into|union|with)\b"
)
_IDENTIFIER = re.compile(r"\b[a-z_][a-z0-9_]*\b")
_TABLE = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*(?:\s*,\s*[a-z_][a-z0-9_]*)*)")
_SUBQUERY_SOURCE = re.compile(r"\b(?:from|join)\s*[(,]|,\s*\(")
_FUNCTION = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(")
_LIMIT = re.compile(r"\blimit\s+(\d+)(?:\s*,\s*(\d+))?(?:\s+offset\s+(\d+))?\s*$")
_NUMBER_OR_STRING = re.compile(r"'[^']*'|\b\d+(?:\.\d+)?\b")


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
    """Accept one read-only SELECT over allowlisted semantic views, with a forced row limit."""
    normalized = " ".join(sql.split()).rstrip(";").strip()
    lowered = normalized.lower()
    if "--" in normalized or "/*" in normalized:
        raise UnsafeSqlError("SQL comments are not allowed")
    if ";" in normalized:
        raise UnsafeSqlError("Only a single statement is allowed")
    if not lowered.startswith("select "):
        raise UnsafeSqlError("Only a single SELECT statement is allowed")
    if FORBIDDEN.search(lowered):
        raise UnsafeSqlError("Only read-only projections over semantic views are allowed")
    if '"' in normalized or "`" in normalized or "[" in normalized:
        raise UnsafeSqlError("Quoted identifiers are not allowed")
    if _SUBQUERY_SOURCE.search(lowered):
        raise UnsafeSqlError("Only allowlisted semantic views may be read")
    if "sqlite_" in lowered or "pragma_" in lowered:
        raise UnsafeSqlError("System catalogs are not readable")
    if "shop_id" in lowered:
        raise UnsafeSqlError("Tenant filtering is applied by the gateway and cannot be restated")

    views = tuple(
        dict.fromkeys(
            table.strip()
            for clause in _TABLE.findall(lowered)
            for table in clause.split(",")
        )
    )
    if not views:
        raise UnsafeSqlError("The query must read an allowlisted semantic view")
    unknown_views = [view for view in views if view not in ALLOWED_VIEWS]
    if unknown_views:
        raise UnsafeSqlError(f"{unknown_views[0]} is not an allowlisted semantic view")

    functions = {name for name in _FUNCTION.findall(lowered)} - set(ALLOWED_VIEWS)
    unsafe_functions = functions - ALLOWED_FUNCTIONS
    if unsafe_functions:
        raise UnsafeSqlError(f"{min(unsafe_functions)} is not an allowlisted function")

    allowed_columns = {column for view in views for column in ALLOWED_VIEWS[view]}
    columns = _referenced_columns(lowered, views, allowed_columns)

    row_limit = ROW_LIMIT
    match = _LIMIT.search(lowered)
    offset = 0
    if match is not None:
        # `LIMIT offset, count` means the second number is the row count.
        requested = int(match.group(2) or match.group(1))
        row_limit = min(requested, ROW_LIMIT)
        offset = int(match.group(1)) if match.group(2) else int(match.group(3) or 0)
        normalized = normalized[: match.start()].strip()
    limit_clause = f"LIMIT {row_limit}" + (f" OFFSET {offset}" if offset else "")
    return AcceptedQuery(
        sql=f"{normalized} {limit_clause}",
        views=views,
        columns=columns,
        row_limit=row_limit,
        timeout_seconds=TIMEOUT_SECONDS,
        principal=PRINCIPAL,
    )


def _referenced_columns(
    lowered: str, views: tuple[str, ...], allowed_columns: set[str]
) -> tuple[str, ...]:
    stripped = _NUMBER_OR_STRING.sub(" ", lowered)
    referenced: list[str] = []
    for identifier in _IDENTIFIER.findall(stripped):
        if identifier in SQL_KEYWORDS or identifier in views or identifier in ALLOWED_FUNCTIONS:
            continue
        if identifier not in allowed_columns:
            raise UnsafeSqlError(f"{identifier} is not an allowlisted column")
        if identifier not in referenced:
            referenced.append(identifier)
    return tuple(referenced)


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
        # Defence in depth: the principal re-checks the envelope it was handed.
        if '"' in query.sql:
            raise UnsafeSqlError(f"{PRINCIPAL} does not read quoted identifiers")
        for clause in _TABLE.findall(query.sql.lower()):
            for table in (name.strip() for name in clause.split(",")):
                if table not in ALLOWED_VIEWS:
                    raise UnsafeSqlError(f"{table} is not readable by {PRINCIPAL}")
        if not query.sql.lower().startswith("select "):
            raise UnsafeSqlError(f"{PRINCIPAL} may only read")
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
