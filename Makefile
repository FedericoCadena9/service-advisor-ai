.PHONY: dev generate-api check check-ollama smoke

dev:
	pnpm exec concurrently --kill-others "UV_CACHE_DIR=.uv-cache uv --directory apps/api run uvicorn service_advisor_api.main:app --host 127.0.0.1 --port 8000" "pnpm --filter web dev --host 127.0.0.1"

generate-api:
	pnpm generate:api

check:
	UV_CACHE_DIR=.uv-cache uv --directory apps/api run ruff check .
	UV_CACHE_DIR=.uv-cache uv --directory apps/api run pytest -q -m "not ollama"
	pnpm check

smoke:
	pnpm --filter web test:e2e

# Real local model. Slow, and skipped entirely when Ollama is not running.
check-ollama:
	UV_CACHE_DIR=.uv-cache uv --directory apps/api run pytest -q -m ollama
