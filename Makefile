default: help

# ── Help ─────────────────────────────────────────────────────────────────
.PHONY: help

help:
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║       llms-gateway — monorepo Makefile               ║"
	@echo "╠══════════════════════════════════════════════════════╣"
	@echo "║                                                      ║"
	@echo "║  TESTING                                             ║"
	@echo "║    make test        Run all tests across monorepo    ║"
	@echo "║    make test-core   modelctl-core library tests      ║"
	@echo "║    make test-api    modelctl-api REST API tests      ║"
	@echo "║    make test-cli    modelctl CLI tests               ║"
	@echo "║                                                      ║"
	@echo "║  EXAMPLES                                            ║"
	@echo "║    make run-example-orch  Orchestrator demo (dry-run)║"
	@echo "║                                                      ║"
	@echo "║  WEB FRONTEND                                        ║"
	@echo "║    make build-web   Build SPA (outputs to static/)   ║"
	@echo "║    make dev-web     Start SvelteKit dev server       ║"
	@echo "║                                                      ║"
	@echo "║  DOCKER                                              ║"
	@echo "║    make build-docker  Build Docker image             ║"
	@echo "║                                                      ║"
	@echo "║  BUILD                                               ║"
	@echo "║    make build      Frontend + Docker image           ║"
	@echo "║                                                      ║"
	@echo "╚══════════════════════════════════════════════════════╝"

# ── Testing ──────────────────────────────────────────────────────────────
# Run all tests across the monorepo
.PHONY: test test-core test-api test-cli

test: test-core test-api test-cli

# modelctl-core library tests
test-core:
	uv run --package modelctl-core pytest -c libs/modelctl-core/pyproject.toml libs/modelctl-core/tests

# modelctl-api REST API tests
test-api:
	uv run --package modelctl-api pytest -c apps/modelctl-api/pyproject.toml apps/modelctl-api/tests

# modelctl CLI tests
test-cli:
	@if ls apps/modelctl/tests/test_*.py >/dev/null 2>&1; then \
		uv run --package modelctl pytest -c apps/modelctl/pyproject.toml apps/modelctl/tests; \
	else \
		echo "  [modelctl]  No tests found — skipping"; \
	fi

# ── Web frontend ──────────────────────────────────────────────────────────
.PHONY: build-web dev-web

# Build the SPA frontend (outputs to apps/modelctl-api/static/)
build-web:
	cd web && bun run build

# Start the SvelteKit dev server
dev-web:
	cd web && bun run dev

# ── Docker ────────────────────────────────────────────────────────────────
.PHONY: build-docker

build-docker: build-web
	docker compose build

# ── Examples ──────────────────────────────────────────────────────────────
.PHONY: run-example-orch

# Run the orchestrator demo (dry-run by default — no Docker needed)
# Loads .env so LLAMACPP_IMAGE is picked up by the orchestrator.
run-example-orch:
	export $$(grep -v '^#' .env | xargs) && \
		uv run python examples/run_llama_with_orchestrator.py --dry-run

# ── Legacy alias ──────────────────────────────────────────────────────────
.PHONY: build
build: build-web build-docker
