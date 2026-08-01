"""What the API needs to be reachable from somewhere other than localhost."""

import pytest
from fastapi.testclient import TestClient

from service_advisor_api.main import app
from service_advisor_api.state import allowed_origins

LOCALHOST = ["http://127.0.0.1:4173", "http://127.0.0.1:5173"]


def test_the_default_origins_are_the_local_dev_servers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert allowed_origins() == LOCALHOST


def test_the_deployment_supplies_its_own_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    """What if the frontend is served from Vercel instead of a dev server?"""
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://demo.vercel.app")

    assert allowed_origins() == ["https://demo.vercel.app"]


def test_several_origins_can_be_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A preview deployment and production answer on different hosts."""
    monkeypatch.setenv(
        "ALLOWED_ORIGINS", "https://demo.vercel.app, https://demo-git-main.vercel.app "
    )

    assert allowed_origins() == ["https://demo.vercel.app", "https://demo-git-main.vercel.app"]


def test_an_empty_setting_falls_back_to_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """What if the variable exists but is blank — never allow every origin by accident."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "   ")

    assert allowed_origins() == LOCALHOST


def test_a_wildcard_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """What if someone sets * to make a CORS problem go away?"""
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")

    with pytest.raises(ValueError, match="wildcard"):
        allowed_origins()


def test_the_browser_preflight_succeeds_for_an_allowed_origin() -> None:
    response = TestClient(app).options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_the_blueprint_and_the_container_agree_on_the_health_check() -> None:
    """A platform that health-checks the wrong path will restart a working service."""
    from pathlib import Path

    import yaml

    repository = Path(__file__).resolve().parents[3]
    blueprint = yaml.safe_load((repository / "render.yaml").read_text())
    service = blueprint["services"][0]

    assert service["dockerfilePath"] == "./apps/api/Dockerfile"
    assert service["dockerContext"] == "./apps/api"
    assert service["healthCheckPath"] == "/health"
    assert {variable["key"] for variable in service["envVars"]} == {
        "ALLOWED_ORIGINS",
        "DEMO_SESSION_SECRET",
    }


def test_the_container_runs_as_an_unprivileged_known_user() -> None:
    """Spaces expects uid 1000; running as root would be refused anyway."""
    import re
    from pathlib import Path

    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text()

    assert re.search(r"--uid 1000\b", dockerfile)
    assert "USER advisor" in dockerfile
