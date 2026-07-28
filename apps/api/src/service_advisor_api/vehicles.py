import sqlite3
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class VehicleSearchResult:
    id: str
    customer_label: str
    vehicle_label: str
    is_demo_data: bool


@dataclass(frozen=True)
class CanonicalVehicle:
    id: str
    customer_label: str
    year: int
    make: str
    model: str
    trim: str
    engine: str
    market: str
    prior_mileage_km: int
    prior_mileage_recorded_on: str
    is_demo_data: bool

    @property
    def vehicle_label(self) -> str:
        return f"{self.year} {self.make} {self.model} {self.trim} {self.engine} {self.market}"


class CanonicalVehicleStore:
    """A deterministic synthetic vehicle record, scoped by shop."""

    def __init__(self) -> None:
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._lock = RLock()
        self._connection.execute(
            """
            CREATE TABLE canonical_vehicles (
                shop_id TEXT NOT NULL,
                id TEXT NOT NULL,
                customer_label TEXT NOT NULL,
                year INTEGER NOT NULL,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                trim TEXT NOT NULL,
                engine TEXT NOT NULL,
                market TEXT NOT NULL,
                prior_mileage_km INTEGER NOT NULL,
                prior_mileage_recorded_on TEXT NOT NULL,
                is_demo_data INTEGER NOT NULL,
                PRIMARY KEY (shop_id, id)
            )
            """
        )

    def seed(self) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT OR IGNORE INTO canonical_vehicles VALUES (
                    'demo-shop', 'honda-civic-2019-lx', 'Demo Customer', 2019,
                    'Honda', 'Civic', 'LX', '2.0L', 'Mexico', 42500, '2026-06-15', 1
                )
                """
            )
            self._connection.commit()

    def search(self, *, shop_id: str, query: str) -> list[VehicleSearchResult]:
        normalized_query = f"%{query.strip().lower()}%"
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, customer_label, year, make, model, trim, engine, market, is_demo_data
                FROM canonical_vehicles
                WHERE shop_id = ? AND (
                    lower(customer_label) LIKE ? OR lower(make) LIKE ? OR lower(model) LIKE ?
                )
                ORDER BY id
                """,
                (shop_id, normalized_query, normalized_query, normalized_query),
            ).fetchall()
        return [
            VehicleSearchResult(
                id=row[0],
                customer_label=row[1],
                vehicle_label=f"{row[2]} {row[3]} {row[4]} {row[5]} {row[6]} {row[7]}",
                is_demo_data=bool(row[8]),
            )
            for row in rows
        ]

    def get(self, *, shop_id: str, vehicle_id: str) -> CanonicalVehicle | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, customer_label, year, make, model, trim, engine, market,
                       prior_mileage_km, prior_mileage_recorded_on, is_demo_data
                FROM canonical_vehicles WHERE shop_id = ? AND id = ?
                """,
                (shop_id, vehicle_id),
            ).fetchone()
        return CanonicalVehicle(*row) if row else None
