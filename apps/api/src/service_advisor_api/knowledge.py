from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal


class QuarantinedSourceError(ValueError):
    pass


class EvidenceUnavailableError(LookupError):
    """Raised when no reviewed rule covers this exact configuration and market."""


class FallbackMarketEvidenceError(EvidenceUnavailableError):
    """Raised when only a labeled fallback-market document exists for this configuration."""

    def __init__(self, market: str, fallback_market: str) -> None:
        super().__init__(
            f"Only a {fallback_market} fallback document exists; it is not combined with "
            f"{market} evidence without explicit review"
        )
        self.market = market
        self.fallback_market = fallback_market


DueState = Literal["overdue", "due_now", "due_soon", "informational"]
NOT_IN_WINDOW = "Mileage is not in the reviewed service window"


@dataclass(frozen=True)
class FixedInterval:
    """One published distance, the shape Toyota uses."""

    km: int
    due_soon_window_km: int = 2_000
    overdue_grace_km: int = 2_000

    def due_state(self, current_mileage_km: int) -> tuple[DueState, str]:
        if current_mileage_km > self.km + self.overdue_grace_km:
            return "overdue", f"Mileage exceeds the {self.km:,} km interval"
        if current_mileage_km >= self.km:
            return "due_now", f"Mileage reached the {self.km:,} km interval"
        if current_mileage_km >= self.km - self.due_soon_window_km:
            return "due_soon", f"Mileage is within {self.due_soon_window_km:,} km of the interval"
        return "informational", NOT_IN_WINDOW


@dataclass(frozen=True)
class RangeInterval:
    """A span rather than a point, the shape Ford publishes alongside its oil-life monitor."""

    earliest_km: int
    latest_km: int
    due_soon_window_km: int = 800

    def due_state(self, current_mileage_km: int) -> tuple[DueState, str]:
        span = f"{self.earliest_km:,}-{self.latest_km:,} km"
        if current_mileage_km > self.latest_km:
            return "overdue", f"Mileage exceeds the {span} interval"
        if current_mileage_km >= self.earliest_km:
            return "due_now", f"Mileage is inside the {span} interval"
        if current_mileage_km >= self.earliest_km - self.due_soon_window_km:
            return "due_soon", f"Mileage is within {self.due_soon_window_km:,} km of {span}"
        return "informational", NOT_IN_WINDOW


@dataclass(frozen=True)
class ConditionInterval:
    """No published distance at all: the vehicle decides.

    Honda's Maintenance Minder computes the service from engine condition, so an odometer
    reading cannot establish that the service is due. Saying otherwise would be inventing a
    number the manual does not contain.
    """

    monitor: str

    def due_state(self, current_mileage_km: int) -> tuple[DueState, str]:
        del current_mileage_km
        return (
            "informational",
            f"{self.monitor} schedules this service by condition, not by distance",
        )


Interval = FixedInterval | RangeInterval | ConditionInterval


@dataclass(frozen=True)
class OfficialSource:
    market: str
    checksum: str
    retrieval_date: str
    citation_page: int
    citation_section: str
    review_state: str
    source_url: str
    fallback_market: bool = False


@dataclass(frozen=True)
class MaintenanceRule:
    service_code: str
    version: str
    citation_page: int
    citation_section: str
    interval: Interval
    immutable: bool = True

    def due_state(self, current_mileage_km: int) -> tuple[DueState, str]:
        return self.interval.due_state(current_mileage_km)


@dataclass(frozen=True)
class ReviewedConfiguration:
    make: str
    model: str
    engine: str
    drivetrain: str
    market: str
    source: OfficialSource
    rule: MaintenanceRule


RETRIEVED_ON = "2026-07-31"


def _source(
    *,
    source_url: str,
    citation_page: int,
    citation_section: str,
    market: str = "United States",
    fallback_market: bool = True,
) -> OfficialSource:
    """Provenance for one reviewed document.

    Every configuration here is a fallback: the research found no public Mexican schedule
    that binds model, year, engine and drivetrain, so the manufacturer's United States
    manual is what was actually read. The checksum covers the URL and the cited location,
    which is what a reviewer verified.
    """
    return OfficialSource(
        market=market,
        checksum=sha256(f"{source_url}#{citation_page}:{citation_section}".encode()).hexdigest(),
        retrieval_date=RETRIEVED_ON,
        citation_page=citation_page,
        citation_section=citation_section,
        review_state="reviewed",
        source_url=source_url,
        fallback_market=fallback_market,
    )


def _configuration(
    make: str,
    model: str,
    engine: str,
    drivetrain: str,
    *,
    service_code: str,
    version: str,
    source_url: str,
    citation_page: int,
    citation_section: str,
    interval: Interval,
) -> ReviewedConfiguration:
    """One reviewed configuration. The vehicle is Mexican; the document is not."""
    return ReviewedConfiguration(
        make=make,
        model=model,
        engine=engine,
        drivetrain=drivetrain,
        market="Mexico",
        source=_source(
            source_url=source_url,
            citation_page=citation_page,
            citation_section=citation_section,
        ),
        rule=MaintenanceRule(
            service_code=service_code,
            version=version,
            citation_page=citation_page,
            citation_section=citation_section,
            interval=interval,
        ),
    )


# Honda publishes no distance for these services: the Maintenance Minder decides, and the
# manual only attaches distances to sub-items such as C2 and C3.
MAINTENANCE_MINDER = "Maintenance Minder"
HONDA_CONFIGURATIONS = (
    _configuration(
        "Honda", "Civic", "2.0L", "FWD",
        service_code="HONDA-A1",
        version="honda-civic-2019-lx-us-v1",
        source_url="https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2019%2FCivic+Sedan%2F2019_Civic_4D_Maintenance_Minder.pdf",
        citation_page=1,
        citation_section="Maintenance Minder Service Codes",
        interval=ConditionInterval(monitor=MAINTENANCE_MINDER),
    ),
    _configuration(
        "Honda", "CR-V", "1.5T", "AWD",
        service_code="HONDA-B1",
        version="honda-crv-2021-ex-us-v1",
        source_url="https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2021%2FCR-V%2F2021_CR-V_Maintenance_Minder_System.PDF",
        citation_page=1,
        citation_section="To Use Maintenance Minder",
        interval=ConditionInterval(monitor=MAINTENANCE_MINDER),
    ),
    _configuration(
        "Honda", "Accord", "1.5T", "FWD",
        service_code="HONDA-A2",
        version="honda-accord-2020-sport-us-v1",
        source_url="https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2020%2FAccord+Sedan%2F2020_Accord_4D_Maintenance_Minder.pdf",
        citation_page=1,
        citation_section="Maintenance Minder Service Codes",
        interval=ConditionInterval(monitor=MAINTENANCE_MINDER),
    ),
)

# Toyota publishes a distance, in miles; these are the converted kilometres.
TOYOTA_CONFIGURATIONS = (
    _configuration(
        "Toyota", "Corolla", "2.0L", "FWD",
        service_code="TOYOTA-10K",
        version="toyota-corolla-2022-le-us-v1",
        source_url="https://assets.sia.toyota.com/publications/en/omms-s/T-MMS-22Corolla/pdf/T-MMS-22Corolla.pdf",
        citation_page=38,
        citation_section="Maintenance Log",
        interval=FixedInterval(km=16_093),
    ),
    _configuration(
        "Toyota", "RAV4", "2.5L", "AWD",
        service_code="TOYOTA-20K",
        version="toyota-rav4-2021-xle-us-v1",
        source_url="https://assets.sia.toyota.com/publications/en/omms-s/T-MMS-21RAV4/pdf/T-MMS-21RAV4.pdf",
        citation_page=38,
        citation_section="Maintenance Log",
        interval=FixedInterval(km=16_093),
    ),
    _configuration(
        "Toyota", "Tacoma", "3.5L", "4WD",
        service_code="TOYOTA-30K",
        version="toyota-tacoma-2020-sr5-us-v1",
        source_url="https://assets.sia.toyota.com/publications/en/omms-s/T-MMS-2086/pdf/T-MMS-2086.pdf",
        citation_page=35,
        citation_section="Using the Maintenance Log Charts",
        interval=FixedInterval(km=12_070),
    ),
)

# Ford publishes a span and an oil-life monitor, and gives 800 km as the grace after the
# dashboard asks for the service.
FORD_CONFIGURATIONS = (
    _configuration(
        "Ford", "F-150", "3.5L", "4WD",
        service_code="FORD-SCHED-A",
        version="ford-f150-2021-xlt-35-4wd-us-v1",
        source_url="https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2021-Ford-F-150-Owners-Manual-version-2_om_EN-US_10_2021.pdf",
        citation_page=667,
        citation_section="Normal Scheduled Maintenance",
        interval=RangeInterval(earliest_km=12_000, latest_km=16_000),
    ),
    _configuration(
        "Ford", "F-150", "5.0L", "RWD",
        service_code="FORD-SCHED-B",
        version="ford-f150-2021-xlt-50-rwd-us-v1",
        source_url="https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2021-Ford-F-150-Owners-Manual-version-2_om_EN-US_10_2021.pdf",
        citation_page=669,
        citation_section="Other Maintenance Items",
        interval=RangeInterval(earliest_km=12_000, latest_km=16_000),
    ),
    _configuration(
        "Ford", "Escape", "1.5L", "FWD",
        service_code="FORD-SCHED-C",
        version="ford-escape-2022-se-us-v1",
        source_url="https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2022-Ford-Escape-Owners-Manual-version-1_om_EN-USA_09.2-2021.pdf",
        citation_page=485,
        citation_section="Normal Scheduled Maintenance",
        interval=RangeInterval(earliest_km=12_000, latest_km=16_000),
    ),
    _configuration(
        "Ford", "Explorer", "2.3L", "AWD",
        service_code="FORD-SCHED-D",
        version="ford-explorer-2020-xlt-us-v1",
        source_url="https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2020-Ford-Explorer-Gas-Hev-Owners-Manual-version-3_om_EN-US_03_2020.pdf",
        citation_page=491,
        citation_section="Normal Scheduled Maintenance",
        interval=RangeInterval(earliest_km=12_070, latest_km=16_093),
    ),
    _configuration(
        "Ford", "Ranger", "2.3L", "4WD",
        service_code="FORD-SCHED-E",
        version="ford-ranger-2021-xlt-us-v1",
        source_url="https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2021-Ford-Ranger-Owners-Manual-version-1_om_EN-US_10_2020.pdf",
        citation_page=419,
        citation_section="Normal Scheduled Maintenance",
        interval=RangeInterval(earliest_km=12_000, latest_km=16_000),
    ),
)

REVIEWED_CONFIGURATIONS: tuple[ReviewedConfiguration, ...] = (
    HONDA_CONFIGURATIONS + TOYOTA_CONFIGURATIONS + FORD_CONFIGURATIONS
)


class KnowledgePack:
    """Immutable reviewed rules, retrievable only for an exact configuration and market."""

    def configurations(self) -> tuple[ReviewedConfiguration, ...]:
        return REVIEWED_CONFIGURATIONS

    def rule_for(
        self,
        *,
        make: str,
        model: str,
        engine: str,
        drivetrain: str,
        market: str,
        allow_fallback_market: bool = False,
    ) -> tuple[OfficialSource, MaintenanceRule]:
        candidates = [
            configuration
            for configuration in REVIEWED_CONFIGURATIONS
            if (configuration.make, configuration.model, configuration.engine, configuration.drivetrain)
            == (make, model, engine, drivetrain)
        ]
        for configuration in candidates:
            if configuration.market == market and not configuration.source.fallback_market:
                return configuration.source, configuration.rule
        fallback = next(
            (configuration for configuration in candidates if configuration.source.fallback_market),
            None,
        )
        if fallback is not None:
            if allow_fallback_market:
                return fallback.source, fallback.rule
            raise FallbackMarketEvidenceError(market, fallback.source.market)
        raise EvidenceUnavailableError(
            f"No reviewed rule covers {make} {model} {engine} {drivetrain} in {market}"
        )

    def reviewed_civic_rule(self) -> tuple[OfficialSource, MaintenanceRule]:
        return self.rule_for(
            make="Honda", model="Civic", engine="2.0L", drivetrain="FWD", market="Mexico",
            allow_fallback_market=True,
        )

    def ingest(self, content: str) -> None:
        suspicious = ("ignore previous instructions", "system prompt", "publish every rule")
        if any(phrase in content.lower() for phrase in suspicious):
            raise QuarantinedSourceError("Suspicious document instruction was quarantined")

    def inspection(self) -> dict[str, dict[str, object]]:
        source, rule = self.reviewed_civic_rule()
        return {"source": asdict(source), "rule": asdict(rule)}
