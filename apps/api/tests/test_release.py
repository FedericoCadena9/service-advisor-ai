import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from service_advisor_api.evaluation import run_suite
from service_advisor_api.main import app
from service_advisor_api.release import (
    IncompatibleMigrationError,
    MigrationStep,
    ReleaseGateError,
    qualify_release,
    release_gates,
    release_manifest,
    validate_migration,
)

REPOSITORY = Path(__file__).resolve().parents[3]


def _cloud_run() -> dict:
    return yaml.safe_load((REPOSITORY / "deploy/cloud-run/service.yaml").read_text())


def test_cloud_run_service_scales_to_zero_with_the_agreed_limits() -> None:
    service = _cloud_run()

    annotations = service["spec"]["template"]["metadata"]["annotations"]
    container = service["spec"]["template"]["spec"]["containers"][0]
    assert annotations["autoscaling.knative.dev/minScale"] == "0"
    assert annotations["autoscaling.knative.dev/maxScale"] == "4"
    assert service["spec"]["template"]["spec"]["containerConcurrency"] == 40
    assert container["resources"]["limits"]["memory"] == "512Mi"
    assert container["startupProbe"]["httpGet"]["path"] == "/health"


def test_abuse_controls_live_in_a_valid_manifest() -> None:
    """What if the operator runs `gcloud run services replace` instead of hand-editing?"""
    service = _cloud_run()
    controls = yaml.safe_load((REPOSITORY / "deploy/cloud-run/cloud-armor.yaml").read_text())

    # A Knative Service rejects unknown top-level fields, so the policy is its own file.
    assert set(service) == {"apiVersion", "kind", "metadata", "spec"}

    assert controls["requestsPerMinutePerIp"] == 60
    assert controls["maxRequestBodyBytes"] == 65536
    assert controls["bannedDurationSeconds"] == 300


def test_vercel_project_builds_the_web_application() -> None:
    config = json.loads((REPOSITORY / "apps/web/vercel.json").read_text())

    assert config["buildCommand"] == "pnpm build"
    assert config["outputDirectory"] == "dist"
    assert config["installCommand"] == "pnpm install --frozen-lockfile"


def test_insforge_services_use_least_privilege_credentials() -> None:
    services = yaml.safe_load((REPOSITORY / "deploy/insforge/services.yaml").read_text())["services"]

    assert set(services) == {"auth", "postgres", "pgvector", "storage", "realtime"}
    assert all(service["enabled"] for service in services.values())
    assert len({service["role"] for service in services.values()}) == 5
    assert services["pgvector"]["permissions"] == ["select"]
    assert "delete" not in services["postgres"]["permissions"]


def test_migration_plan_is_backward_compatible() -> None:
    steps = validate_migration()

    assert next(step.name for step in steps) == "create_demo_overlays"
    with pytest.raises(IncompatibleMigrationError):
        validate_migration([MigrationStep("drop_legacy_quotes", "drop_table")])


def test_manifest_records_release_model_prompt_rule_and_dataset_versions() -> None:
    manifest = release_manifest()

    assert manifest.release_version == "public-demo-v1"
    assert manifest.model_version == "deterministic-demo"
    assert manifest.prompt_version == "advisor-prompt-v1"
    assert manifest.dataset_version == "canonical-100-v1"
    assert len(manifest.rule_versions) == 11


def test_automatic_gates_block_a_release_but_the_live_gate_does_not() -> None:
    gates = release_gates(health_ok=True, smoke_ok=True, evaluation=run_suite())

    assert qualify_release(gates) == gates
    assert {gate.name: gate.passed for gate in gates}["live_model_promotion"] is False
    with pytest.raises(ReleaseGateError, match="smoke"):
        qualify_release(release_gates(health_ok=True, smoke_ok=False, evaluation=run_suite()))


def test_readiness_reports_cold_start_then_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("service_advisor_api.state.served_first_request", False)
    client = TestClient(app)

    first = client.get("/readiness").json()
    second = client.get("/readiness").json()

    assert first["cold_start"] is True
    assert first["status"] == "waking"
    assert second["cold_start"] is False
    assert second["status"] == "ready"
    assert second["manifest"]["release_version"] == "public-demo-v1"
    assert "create_semantic_views" in second["migration_steps"]


def test_readiness_fails_closed_when_a_gate_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMOKE_CHECK_PASSED", "false")

    response = TestClient(app).get("/readiness")

    assert response.status_code == 503
    assert "smoke" in response.json()["detail"]


def test_a_visitor_cannot_flip_release_gates_from_the_query_string() -> None:
    """What if a public visitor passes the gate flags instead of the deployment setting them?"""
    response = TestClient(app).get(
        "/readiness", params={"smoke_ok": False, "live_model_promotion_approved": True}
    )

    gates = {gate["name"]: gate["passed"] for gate in response.json()["gates"]}
    assert response.status_code == 200
    assert gates["smoke"] is True
    assert gates["live_model_promotion"] is False


def test_the_operator_flips_the_manual_promotion_gate_through_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVE_MODEL_PROMOTION_APPROVED", "true")

    response = TestClient(app).get("/readiness")

    gates = {gate["name"]: gate["passed"] for gate in response.json()["gates"]}
    assert gates["live_model_promotion"] is True


def test_release_manifest_is_public() -> None:
    response = TestClient(app).get("/release")

    assert response.status_code == 200
    assert response.json()["dataset_version"] == "canonical-100-v1"


def test_public_demo_documentation_records_the_agreed_sections() -> None:
    documentation = (REPOSITORY / "docs/deployment/public-demo.md").read_text()

    for heading in ("## Setup", "## Release gates", "## Provider limits", "## Recovery behavior"):
        assert heading in documentation
    assert "Manual live-model promotion gate" in documentation
    assert "LIVE_MODEL_PROMOTION_APPROVED=true" in documentation
    assert "never from a query string" in documentation
