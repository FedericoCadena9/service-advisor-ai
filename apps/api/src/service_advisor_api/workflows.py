from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class AdvisorRun:
    id: str
    shop_id: str
    demo_session_id: str
    events: tuple[str, ...]
    decision: str | None = None
    command_executed: bool = False


class AdvisorWorkflowStore:
    def __init__(self) -> None:
        self._runs: dict[str, AdvisorRun] = {}

    def start(self, shop_id: str, demo_session_id: str) -> AdvisorRun:
        run = AdvisorRun(str(uuid4()), shop_id, demo_session_id, ("started", "context_loaded", "awaiting_human_review"))
        self._runs[run.id] = run
        return run

    def reconnect(self, run_id: str, shop_id: str, demo_session_id: str) -> AdvisorRun:
        run = self._runs[run_id]
        if (run.shop_id, run.demo_session_id) != (shop_id, demo_session_id):
            raise PermissionError("Run is outside this demo session")
        return run

    def decide(self, run_id: str, decision: str) -> AdvisorRun:
        run = self._runs[run_id]
        if run.decision is not None:
            return run
        updated = AdvisorRun(run.id, run.shop_id, run.demo_session_id, run.events + ("approved",), decision, decision == "approve")
        self._runs[run_id] = updated
        return updated
