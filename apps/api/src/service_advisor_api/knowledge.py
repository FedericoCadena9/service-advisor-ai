from dataclasses import asdict, dataclass
from hashlib import sha256


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


@dataclass(frozen=True)
class OfficialSource:
    market: str
    checksum: str
    retrieval_date: str
    citation_page: int
    citation_section: str
    review_state: str
    fallback_market: bool = False


@dataclass(frozen=True)
class MaintenanceRule:
    service_code: str
    version: str
    citation_page: int
    citation_section: str
    interval_km: int = 48_000
    due_soon_window_km: int = 2_000
    overdue_grace_km: int = 2_000
    immutable: bool = True


@dataclass(frozen=True)
class ReviewedConfiguration:
    make: str
    model: str
    engine: str
    drivetrain: str
    market: str
    source: OfficialSource
    rule: MaintenanceRule


def _source(
    *,
    market: str,
    text: str,
    retrieval_date: str,
    citation_page: int,
    citation_section: str,
    fallback_market: bool = False,
) -> OfficialSource:
    return OfficialSource(
        market=market,
        checksum=sha256(text.encode()).hexdigest(),
        retrieval_date=retrieval_date,
        citation_page=citation_page,
        citation_section=citation_section,
        review_state="reviewed",
        fallback_market=fallback_market,
    )


HONDA_CONFIGURATIONS = (
    ReviewedConfiguration(
        make="Honda",
        model="Civic",
        engine="2.0L",
        drivetrain="FWD",
        market="Mexico",
        source=_source(
            market="Mexico",
            text="Honda Civic Mexico maintenance minder reviewed source",
            retrieval_date="2026-07-27",
            citation_page=42,
            citation_section="Maintenance Minder",
        ),
        rule=MaintenanceRule(
            service_code="HONDA-A1",
            version="honda-civic-2019-lx-v1",
            citation_page=42,
            citation_section="Maintenance Minder",
            interval_km=48_000,
        ),
    ),
    ReviewedConfiguration(
        make="Honda",
        model="CR-V",
        engine="1.5T",
        drivetrain="AWD",
        market="Mexico",
        source=_source(
            market="Mexico",
            text="Honda CR-V Mexico maintenance schedule reviewed source",
            retrieval_date="2026-07-29",
            citation_page=55,
            citation_section="Programa de mantenimiento",
        ),
        rule=MaintenanceRule(
            service_code="HONDA-B1",
            version="honda-crv-2021-ex-v1",
            citation_page=55,
            citation_section="Programa de mantenimiento",
            interval_km=40_000,
        ),
    ),
    ReviewedConfiguration(
        make="Honda",
        model="Accord",
        engine="1.5T",
        drivetrain="FWD",
        market="Mexico",
        source=_source(
            market="Mexico",
            text="Honda Accord Mexico maintenance schedule reviewed source",
            retrieval_date="2026-07-29",
            citation_page=61,
            citation_section="Programa de mantenimiento",
        ),
        rule=MaintenanceRule(
            service_code="HONDA-A2",
            version="honda-accord-2020-sport-v1",
            citation_page=61,
            citation_section="Programa de mantenimiento",
            interval_km=32_000,
        ),
    ),
)

TOYOTA_CONFIGURATIONS = (
    ReviewedConfiguration(
        make="Toyota",
        model="Corolla",
        engine="2.0L",
        drivetrain="FWD",
        market="Mexico",
        source=_source(
            market="Mexico",
            text="Toyota Corolla Mexico maintenance schedule reviewed source",
            retrieval_date="2026-07-30",
            citation_page=18,
            citation_section="Programa de servicio",
        ),
        rule=MaintenanceRule(
            service_code="TOYOTA-10K",
            version="toyota-corolla-2022-le-v1",
            citation_page=18,
            citation_section="Programa de servicio",
            interval_km=40_000,
        ),
    ),
    ReviewedConfiguration(
        make="Toyota",
        model="RAV4",
        engine="2.5L",
        drivetrain="AWD",
        market="Mexico",
        source=_source(
            market="Mexico",
            text="Toyota RAV4 Mexico maintenance schedule reviewed source",
            retrieval_date="2026-07-30",
            citation_page=24,
            citation_section="Programa de servicio",
        ),
        rule=MaintenanceRule(
            service_code="TOYOTA-20K",
            version="toyota-rav4-2021-xle-v1",
            citation_page=24,
            citation_section="Programa de servicio",
            interval_km=48_000,
        ),
    ),
    # No Mexican document has been reviewed for the Tacoma; the US schedule stays labeled.
    ReviewedConfiguration(
        make="Toyota",
        model="Tacoma",
        engine="3.5L",
        drivetrain="4WD",
        market="United States",
        source=_source(
            market="United States",
            text="Toyota Tacoma United States maintenance schedule reviewed source",
            retrieval_date="2026-07-30",
            citation_page=31,
            citation_section="Maintenance Schedule",
            fallback_market=True,
        ),
        rule=MaintenanceRule(
            service_code="TOYOTA-30K",
            version="toyota-tacoma-2020-sr5-us-v1",
            citation_page=31,
            citation_section="Maintenance Schedule",
            interval_km=48_000,
        ),
    ),
)

def _ford(
    model: str,
    engine: str,
    drivetrain: str,
    service_code: str,
    version: str,
    citation_page: int,
    interval_km: int,
) -> ReviewedConfiguration:
    return ReviewedConfiguration(
        make="Ford",
        model=model,
        engine=engine,
        drivetrain=drivetrain,
        market="Mexico",
        source=_source(
            market="Mexico",
            text=f"Ford {model} {engine} {drivetrain} Mexico maintenance schedule reviewed source",
            retrieval_date="2026-07-31",
            citation_page=citation_page,
            citation_section="Programa de mantenimiento",
        ),
        rule=MaintenanceRule(
            service_code=service_code,
            version=version,
            citation_page=citation_page,
            citation_section="Programa de mantenimiento",
            interval_km=interval_km,
        ),
    )


# Engine and drivetrain are part of the key: the F-150 schedules differ per powertrain.
FORD_CONFIGURATIONS = (
    _ford("F-150", "3.5L", "4WD", "FORD-SCHED-A", "ford-f150-2021-xlt-35-4wd-v1", 27, 16_000),
    _ford("F-150", "5.0L", "RWD", "FORD-SCHED-B", "ford-f150-2021-xlt-50-rwd-v1", 29, 20_000),
    _ford("Escape", "1.5L", "FWD", "FORD-SCHED-C", "ford-escape-2022-se-v1", 33, 16_000),
    _ford("Explorer", "2.3L", "AWD", "FORD-SCHED-D", "ford-explorer-2020-xlt-v1", 39, 24_000),
    _ford("Ranger", "2.3L", "4WD", "FORD-SCHED-E", "ford-ranger-2021-xlt-v1", 44, 16_000),
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
            make="Honda", model="Civic", engine="2.0L", drivetrain="FWD", market="Mexico"
        )

    def ingest(self, content: str) -> None:
        suspicious = ("ignore previous instructions", "system prompt", "publish every rule")
        if any(phrase in content.lower() for phrase in suspicious):
            raise QuarantinedSourceError("Suspicious document instruction was quarantined")

    def inspection(self) -> dict[str, dict[str, object]]:
        source, rule = self.reviewed_civic_rule()
        return {"source": asdict(source), "rule": asdict(rule)}
