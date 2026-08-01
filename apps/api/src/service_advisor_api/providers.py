import json
import os
import urllib.error
import urllib.request
from typing import Protocol, runtime_checkable

DEFAULT_TIMEOUT_SECONDS = 8.0
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3.5:9b"


class ProviderError(RuntimeError):
    """Base class for every way a language provider can fail to answer."""


class ProviderTimeoutError(ProviderError):
    """Raised when the provider did not answer inside its budget."""


class ProviderUnavailableError(ProviderError):
    """Raised when the provider could not be reached or refused the call."""


@runtime_checkable
class LanguageProvider(Protocol):
    """The only thing the Advisor asks of a model: turn a prompt into text.

    Whatever comes back is untrusted; grounding is enforced by the caller.
    """

    name: str

    def complete(self, prompt: str, *, timeout_seconds: float) -> str: ...


class DeterministicProvider:
    """No model, no network. Returns nothing so the caller uses its grounded fallback."""

    name = "deterministic"

    def complete(self, prompt: str, *, timeout_seconds: float) -> str:
        del prompt, timeout_seconds
        return ""


class OllamaProvider:
    """A local model, opted into for development. Never the default."""

    name = "ollama"

    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        self.host = host or os.environ.get("OLLAMA_HOST", OLLAMA_HOST)
        self.model = model or os.environ.get("OLLAMA_MODEL", OLLAMA_MODEL)

    def complete(self, prompt: str, *, timeout_seconds: float) -> str:
        request = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(
                {"model": self.model, "prompt": prompt, "stream": False}
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read())
        except TimeoutError as error:
            raise ProviderTimeoutError(f"{self.model} did not answer in time") from error
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", error)
            if isinstance(reason, TimeoutError):
                raise ProviderTimeoutError(f"{self.model} did not answer in time") from error
            raise ProviderUnavailableError(f"{self.host} is unreachable: {reason}") from error
        except (json.JSONDecodeError, ValueError) as error:
            raise ProviderUnavailableError(f"{self.model} returned unreadable output") from error
        return str(payload.get("response", ""))


def select_provider() -> LanguageProvider:
    """Deterministic unless the deployment explicitly asks for something else.

    An unknown name falls back rather than failing: a misconfigured demo still answers,
    grounded, instead of returning errors to the Advisor.
    """
    requested = os.environ.get("ADVISOR_PROVIDER", "deterministic").strip().lower()
    if requested == "ollama":
        return OllamaProvider()
    return DeterministicProvider()
