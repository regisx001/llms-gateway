default: build

.PHONY: build build-web build-docker dev-web

# Build the SPA frontend (outputs to apps/modelctl-api/static/)
build-web:
	cd web && bun run build

# Build the Docker image (requires build-web first)
build-docker:
	docker compose build

# Build everything — frontend + Docker image
build: build-web build-docker

# Start the SvelteKit dev server
dev-web:
	cd web && bun run dev
