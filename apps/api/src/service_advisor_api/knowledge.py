from dataclasses import asdict, dataclass
from hashlib import sha256


class QuarantinedSourceError(ValueError):
    pass


class EvidenceUnavailableError(LookupError):
    """Raised when no reviewed rule covers this exact configuration and market."""


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

REVIEWED_CONFIGURATIONS: tuple[ReviewedConfiguration, ...] = HONDA_CONFIGURATIONS


class KnowledgePack:
    """Immutable reviewed rules, retrievable only for an exact configuration and market."""

    def configurations(self) -> tuple[ReviewedConfiguration, ...]:
        return REVIEWED_CONFIGURATIONS

    def rule_for(
        self, *, make: str, model: str, engine: str, drivetrain: str, market: str
    ) -> tuple[OfficialSource, MaintenanceRule]:
        for configuration in REVIEWED_CONFIGURATIONS:
            if (
                configuration.make,
                configuration.model,
                configuration.engine,
                configuration.drivetrain,
                configuration.market,
            ) == (make, model, engine, drivetrain, market):
                return configuration.source, configuration.rule
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
