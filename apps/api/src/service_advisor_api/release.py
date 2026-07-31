from collections.abc import Sequence
from dataclasses import dataclass

from service_advisor_api.evaluation import DATASET_VERSION, PROMPT_VERSION, THRESHOLDS, SuiteReport
from service_advisor_api.knowledge import KnowledgePack

RELEASE_VERSION = "public-demo-v1"
MODEL_VERSION = "deterministic-demo"
BACKWARD_COMPATIBLE_OPERATIONS = ("create_table", "create_view", "add_nullable_column", "add_index")


class IncompatibleMigrationError(RuntimeError):
    """Raised when a release step would break a running previous revision."""


class ReleaseGateError(RuntimeError):
    """Raised when a release gate has not been satisfied."""


@dataclass(frozen=True)
class MigrationStep:
    name: str
    operation: str


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ReleaseManifest:
    release_version: str
    model_version: str
    prompt_version: str
    dataset_version: str
    rule_versions: tuple[str, ...]


MIGRATION_PLAN = (
    MigrationStep("create_demo_overlays", "create_table"),
    MigrationStep("create_canonical_vehicles", "create_table"),
    MigrationStep("create_semantic_views", "create_view"),
    MigrationStep("add_vehicle_drivetrain", "add_nullable_column"),
    MigrationStep("index_quote_audit_review", "add_index"),
)


def release_manifest() -> ReleaseManifest:
    return ReleaseManifest(
        release_version=RELEASE_VERSION,
        model_version=MODEL_VERSION,
        prompt_version=PROMPT_VERSION,
        dataset_version=DATASET_VERSION,
        rule_versions=tuple(
            sorted(configuration.rule.version for configuration in KnowledgePack().configurations())
        ),
    )


def validate_migration(steps: Sequence[MigrationStep] = MIGRATION_PLAN) -> tuple[MigrationStep, ...]:
    """Every release step must keep the previous revision serving during rollout."""
    for step in steps:
        if step.operation not in BACKWARD_COMPATIBLE_OPERATIONS:
            raise IncompatibleMigrationError(
                f"{step.name} uses {step.operation}, which is not backward compatible"
            )
    return tuple(steps)


def release_gates(
    *,
    health_ok: bool,
    smoke_ok: bool,
    evaluation: SuiteReport,
    live_model_promotion_approved: bool = False,
) -> tuple[GateResult, ...]:
    """Deterministic gates run on every deploy; the live-model gate stays manual."""
    return (
        GateResult("migration", _migration_ok(), "backward-compatible steps only"),
        GateResult("health", health_ok, "GET /health returned healthy"),
        GateResult("smoke", smoke_ok, "browser health journey passed"),
        GateResult(
            "deterministic_evaluation",
            evaluation.thresholds_met,
            f"overall {evaluation.scores['overall']:.2f} against {THRESHOLDS['overall']}",
        ),
        GateResult(
            "live_model_promotion",
            live_model_promotion_approved,
            "manual 100-case live-model promotion gate",
        ),
    )


def qualify_release(gates: Sequence[GateResult]) -> tuple[GateResult, ...]:
    """Automatic gates must pass to deploy; the manual gate only blocks live-model promotion."""
    blocking = [gate for gate in gates if gate.name != "live_model_promotion" and not gate.passed]
    if blocking:
        raise ReleaseGateError(f"{blocking[0].name} gate failed: {blocking[0].detail}")
    return tuple(gates)


def _migration_ok() -> bool:
    try:
        validate_migration()
    except IncompatibleMigrationError:  # pragma: no cover - plan is validated in tests
        return False
    return True
