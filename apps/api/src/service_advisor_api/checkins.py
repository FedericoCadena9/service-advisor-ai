import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from threading import RLock
from typing import Literal

UseProfile = Literal["normal", "severe"]


class InvalidCheckinError(ValueError):
    """Raised when a check-in cannot safely begin a recommendation."""


@dataclass(frozen=True)
class Checkin:
    current_mileage_km: int
    prior_mileage_km: int
    checked_in_on: str
    use_profile: UseProfile
    severe_use_factors: tuple[str, ...]
    concern: str
    appointment_window: str
    message_consent: bool


def validate_checkin(
    *,
    current_mileage_km: int,
    prior_mileage_km: int,
    checked_in_on: str,
    use_profile: UseProfile,
    severe_use_factors: list[str],
    concern: str,
    appointment_window: str,
    message_consent: bool,
) -> Checkin:
    if current_mileage_km < prior_mileage_km:
        raise InvalidCheckinError("Mileage cannot be below prior recorded mileage")
    try:
        date.fromisoformat(checked_in_on)
    except ValueError as error:
        raise InvalidCheckinError("Check-in date must use ISO format") from error
    if use_profile == "severe" and not severe_use_factors:
        raise InvalidCheckinError("Severe use requires at least one severe-use factor")
    if use_profile == "normal" and severe_use_factors:
        raise InvalidCheckinError("Normal use cannot include severe-use factors")
    if not concern.strip():
        raise InvalidCheckinError("A written concern is required")
    if not appointment_window.strip():
        raise InvalidCheckinError("An appointment window is required")
    return Checkin(
        current_mileage_km=current_mileage_km,
        prior_mileage_km=prior_mileage_km,
        checked_in_on=checked_in_on,
        use_profile=use_profile,
        severe_use_factors=tuple(severe_use_factors),
        concern=concern.strip(),
        appointment_window=appointment_window.strip(),
        message_consent=message_consent,
    )


class CheckinStore:
    def __init__(self) -> None:
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._lock = RLock()
        self._connection.execute(
            """
            CREATE TABLE checkins (
                shop_id TEXT NOT NULL,
                demo_session_id TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                current_mileage_km INTEGER NOT NULL,
                prior_mileage_km INTEGER NOT NULL,
                checked_in_on TEXT NOT NULL,
                use_profile TEXT NOT NULL,
                severe_use_factors TEXT NOT NULL,
                concern TEXT NOT NULL,
                appointment_window TEXT NOT NULL,
                message_consent INTEGER NOT NULL,
                PRIMARY KEY (shop_id, demo_session_id, vehicle_id)
            )
            """
        )

    def save(self, *, shop_id: str, demo_session_id: str, vehicle_id: str, checkin: Checkin) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO checkins VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shop_id,
                    demo_session_id,
                    vehicle_id,
                    checkin.current_mileage_km,
                    checkin.prior_mileage_km,
                    checkin.checked_in_on,
                    checkin.use_profile,
                    json.dumps(checkin.severe_use_factors),
                    checkin.concern,
                    checkin.appointment_window,
                    checkin.message_consent,
                ),
            )
            self._connection.commit()

    def get(self, *, shop_id: str, demo_session_id: str, vehicle_id: str) -> Checkin | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT current_mileage_km, prior_mileage_km, checked_in_on, use_profile,
                       severe_use_factors, concern, appointment_window, message_consent
                FROM checkins WHERE shop_id = ? AND demo_session_id = ? AND vehicle_id = ?
                """,
                (shop_id, demo_session_id, vehicle_id),
            ).fetchone()
        if row is None:
            return None
        return Checkin(
            current_mileage_km=row[0],
            prior_mileage_km=row[1],
            checked_in_on=row[2],
            use_profile=row[3],
            severe_use_factors=tuple(json.loads(row[4])),
            concern=row[5],
            appointment_window=row[6],
            message_consent=bool(row[7]),
        )
