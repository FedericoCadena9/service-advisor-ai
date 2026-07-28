import sqlite3
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class DemoOverlay:
    shop_id: str
    demo_session_id: str
    role: str
    generation: int


class OverlayStore:
    """Stores mutable demo state under the signed session boundary."""

    def __init__(self) -> None:
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._lock = RLock()
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS demo_overlays (
                shop_id TEXT NOT NULL,
                demo_session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                generation INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (shop_id, demo_session_id)
            )
            """
        )

    def get_or_create(self, *, shop_id: str, demo_session_id: str, role: str) -> DemoOverlay:
        with self._lock:
            self._connection.execute(
                """
                INSERT OR IGNORE INTO demo_overlays (shop_id, demo_session_id, role)
                VALUES (?, ?, ?)
                """,
                (shop_id, demo_session_id, role),
            )
            self._connection.commit()
            return self._find(shop_id=shop_id, demo_session_id=demo_session_id)

    def reset(self, *, shop_id: str, demo_session_id: str, role: str) -> DemoOverlay:
        with self._lock:
            self.get_or_create(shop_id=shop_id, demo_session_id=demo_session_id, role=role)
            self._connection.execute(
                """
                UPDATE demo_overlays
                SET generation = generation + 1
                WHERE shop_id = ? AND demo_session_id = ?
                """,
                (shop_id, demo_session_id),
            )
            self._connection.commit()
            return self._find(shop_id=shop_id, demo_session_id=demo_session_id)

    def list_for_shop(self, shop_id: str) -> list[DemoOverlay]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT shop_id, demo_session_id, role, generation
                FROM demo_overlays
                WHERE shop_id = ?
                ORDER BY demo_session_id
                """,
                (shop_id,),
            ).fetchall()
        return [DemoOverlay(*row) for row in rows]

    def _find(self, *, shop_id: str, demo_session_id: str) -> DemoOverlay:
        row = self._connection.execute(
            """
            SELECT shop_id, demo_session_id, role, generation
            FROM demo_overlays
            WHERE shop_id = ? AND demo_session_id = ?
            """,
            (shop_id, demo_session_id),
        ).fetchone()
        if row is None:  # pragma: no cover - protected by get_or_create
            raise RuntimeError("Demo overlay was not created")
        return DemoOverlay(*row)
