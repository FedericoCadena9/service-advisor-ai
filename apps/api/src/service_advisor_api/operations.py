import sqlite3
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class PartAvailability:
    part_number: str
    on_hand: int
    restock_status: str
    restock_eta: str | None


@dataclass(frozen=True)
class BaySlot:
    id: str
    starts_at: str
    capacity_minutes: int


class OperationsStore:
    """Tenant-scoped parts inventory and bay capacity used by quote drafting."""

    def __init__(self) -> None:
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._lock = RLock()
        self._connection.execute(
            """
            CREATE TABLE parts_inventory (
                shop_id TEXT NOT NULL,
                part_number TEXT NOT NULL,
                on_hand INTEGER NOT NULL,
                restock_status TEXT NOT NULL,
                restock_eta TEXT,
                PRIMARY KEY (shop_id, part_number)
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE bay_slots (
                shop_id TEXT NOT NULL,
                id TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                capacity_minutes INTEGER NOT NULL,
                PRIMARY KEY (shop_id, id)
            )
            """
        )

    def seed(self) -> None:
        with self._lock:
            self._connection.executemany(
                "INSERT OR IGNORE INTO parts_inventory VALUES (?, ?, ?, ?, ?)",
                (
                    ("demo-shop", "HON-OIL-0W20", 12, "in_stock", None),
                    ("demo-shop", "HON-FILTER-15400", 4, "in_stock", None),
                    ("demo-shop", "HON-CABIN-80292", 0, "backordered", "2026-08-14"),
                    ("demo-shop", "HON-BRAKE-45022", 0, "discontinued", None),
                ),
            )
            self._connection.executemany(
                "INSERT OR IGNORE INTO bay_slots VALUES (?, ?, ?, ?)",
                (
                    ("demo-shop", "bay-1-morning", "2026-08-03T09:00:00", 90),
                    ("demo-shop", "bay-2-afternoon", "2026-08-03T14:00:00", 180),
                ),
            )
            self._connection.commit()

    def part(self, shop_id: str, part_number: str) -> PartAvailability | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT part_number, on_hand, restock_status, restock_eta
                FROM parts_inventory WHERE shop_id = ? AND part_number = ?
                """,
                (shop_id, part_number),
            ).fetchone()
        return PartAvailability(*row) if row else None

    def slots(self, shop_id: str) -> tuple[BaySlot, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, starts_at, capacity_minutes FROM bay_slots
                WHERE shop_id = ? ORDER BY starts_at
                """,
                (shop_id,),
            ).fetchall()
        return tuple(BaySlot(*row) for row in rows)
