from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class ServiceRecord:
    id: str
    service_code: str
    status: str
    odometer_km: int = 0


class CivicServiceHistoryStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], tuple[ServiceRecord, ...]] = {}

    # A shop's fleet is not all in the same state: some vehicles were serviced recently,
    # some are coming due, and some were neglected. Each record remembers the odometer,
    # which is what makes an interval a cycle rather than a milestone.
    SEEDED_HISTORY: ClassVar[dict[str, tuple[ServiceRecord, ...]]] = {
        "honda-civic-2019-lx": (
            ServiceRecord("complete-honda-a1-2026-05", "HONDA-A1", "completed", 38_000),
            ServiceRecord("decline-honda-a1-2026-06", "HONDA-A1", "declined", 38_000),
        ),
        "toyota-corolla-2022-le": (
            ServiceRecord("complete-toyota-10k-2026-04", "TOYOTA-10K", "completed", 32_000),
        ),
        "toyota-rav4-2021-xle": (
            ServiceRecord("complete-toyota-20k-2026-02", "TOYOTA-20K", "completed", 32_186),
        ),
        "ford-explorer-2020-xlt": (
            ServiceRecord("complete-ford-d-2026-03", "FORD-SCHED-D", "completed", 12_070),
        ),
        "ford-escape-2022-se": (
            ServiceRecord("complete-ford-c-2026-06", "FORD-SCHED-C", "completed", 13_500),
        ),
    }

    def seed(self) -> None:
        for vehicle_id, records in self.SEEDED_HISTORY.items():
            self._records[("demo-shop", vehicle_id)] = records

    def add_record(self, shop_id: str, vehicle_id: str, record: ServiceRecord) -> None:
        key = (shop_id, vehicle_id)
        self._records[key] = self._records.get(key, ()) + (record,)

    def remove_record(self, shop_id: str, vehicle_id: str, record_id: str) -> None:
        key = (shop_id, vehicle_id)
        self._records[key] = tuple(
            record for record in self._records.get(key, ()) if record.id != record_id
        )

    def completed(self, shop_id: str, vehicle_id: str) -> tuple[ServiceRecord, ...]:
        return tuple(record for record in self._records.get((shop_id, vehicle_id), ()) if record.status == "completed")

    def declined(self, shop_id: str, vehicle_id: str) -> tuple[ServiceRecord, ...]:
        return tuple(record for record in self._records.get((shop_id, vehicle_id), ()) if record.status == "declined")
