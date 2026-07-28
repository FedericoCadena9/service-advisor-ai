from dataclasses import asdict, dataclass
from hashlib import sha256


class QuarantinedSourceError(ValueError):
    pass


@dataclass(frozen=True)
class OfficialSource:
    market: str
    checksum: str
    retrieval_date: str
    citation_page: int
    citation_section: str
    review_state: str


@dataclass(frozen=True)
class MaintenanceRule:
    service_code: str
    version: str
    citation_page: int
    citation_section: str
    immutable: bool = True


class KnowledgePack:
    def reviewed_civic_rule(self) -> tuple[OfficialSource, MaintenanceRule]:
        source_text = "Honda Civic Mexico maintenance minder reviewed source"
        source = OfficialSource(
            market="Mexico",
            checksum=sha256(source_text.encode()).hexdigest(),
            retrieval_date="2026-07-27",
            citation_page=42,
            citation_section="Maintenance Minder",
            review_state="reviewed",
        )
        return source, MaintenanceRule(
            service_code="HONDA-A1",
            version="honda-civic-2019-lx-v1",
            citation_page=42,
            citation_section="Maintenance Minder",
        )

    def ingest(self, content: str) -> None:
        suspicious = ("ignore previous instructions", "system prompt", "publish every rule")
        if any(phrase in content.lower() for phrase in suspicious):
            raise QuarantinedSourceError("Suspicious document instruction was quarantined")

    def inspection(self) -> dict[str, dict[str, object]]:
        source, rule = self.reviewed_civic_rule()
        return {"source": asdict(source), "rule": asdict(rule)}
