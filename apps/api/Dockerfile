# Cloud Run builds this image; the service definition in deploy/cloud-run/service.yaml
# expects it to listen on $PORT and to answer /health during startup.
FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.9.29 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies resolve from the lockfile alone, so a source edit does not refetch them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.13-slim AS runtime

# The service holds no secrets on disk and needs no shell tools; run it unprivileged.
# Spaces runs the container as uid 1000; the same user is unprivileged on Cloud Run.
RUN useradd --create-home --uid 1000 advisor
WORKDIR /app
COPY --from=build --chown=advisor:advisor /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PORT=8080
USER advisor
EXPOSE 8080

CMD ["sh", "-c", "uvicorn service_advisor_api.main:app --host 0.0.0.0 --port ${PORT}"]
