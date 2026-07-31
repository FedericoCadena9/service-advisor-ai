from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceRecord:
    id: str
    service_code: str
    status: str


class CivicServiceHistoryStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], tuple[ServiceRecord, ...]] = {}

    def seed(self) -> None:
        self._records[("demo-shop", "honda-civic-2019-lx")] = (
            ServiceRecord("complete-honda-a1-2026-05", "HONDA-A1", "completed"),
            ServiceRecord("decline-honda-a1-2026-06", "HONDA-A1", "declined"),
        )

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
