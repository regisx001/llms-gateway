# LLMs Gateway

LLM inference gateway with model management — search, download, and serve GGUF models via `llama.cpp`.

## Anatomy

```
.
├── apps/
│   ├── modelctl              # CLI app (modelctl command)
│   │   └── src/modelctl/cli.py
│   └── modelctl-api          # REST API (FastAPI, runs inside llama-server container)
│       ├── pyproject.toml
│       ├── src/modelctl_api/
│       │   ├── main.py       # app factory, lifespan, CORS
│       │   ├── config.py     # pydantic-settings
│       │   ├── dependencies.py
│       │   ├── models/       # Pydantic schemas
│       │   ├── routers/      # HTTP endpoints
│       │   └── services/     # business logic
│       └── tests/            # API test suite
├── libs/modelctl-core        # core library
│   └── src/modelctl_core/
│       ├── models.py         # data classes (Model, Artifact, Download)
│       ├── registry.py       # JSON file persistence
│       ├── huggingface.py    # HuggingFace API client
│       └── validator.py      # file validation
├── registry/                 # JSON files tracking models & downloads
├── storage/                  # downloaded model files
├── tests/                    # core library tests
├── pyproject.toml            # uv workspace root
├── docker-compose.yml        # runs llama-server + modelctl-api + modelctl
├── Dockerfile.llamacpp.server  # single image: llama-server + modelctl-cli + modelctl-api
└── entrypoint.sh             # container startup script (starts both services)
```

## Setup

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install everything
uv sync
```

## Usage

### CLI

```bash
# Search and install a model
uv run modelctl search llama
uv run modelctl inspect unsloth/gemma-4-E2B-it-qat-GGUF
uv run modelctl install unsloth/gemma-4-E2B-it-qat-GGUF gemma-4-E2B-it-qat-UD-Q2_K_XL.gguf

# List installed models
uv run modelctl list

# Activate model for serving
uv run modelctl activate <model-id>
```

### REST API

```bash
# Start dev server
uv run uvicorn modelctl_api.main:app --reload --port 8000

# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/api/v1/models

# Search HuggingFace
curl "http://localhost:8000/api/v1/search?q=llama&limit=5"

# Inspect a repo
curl "http://localhost:8000/api/v1/search/inspect?repo_id=unsloth/gemma-4-E2B-it-qat-GGUF"

# Install a model
curl -X POST http://localhost:8000/api/v1/models/install \
  -H "Content-Type: application/json" \
  -d '{"repo_id": "unsloth/gemma-4-E2B-it-qat-GGUF", "filename": "gemma-4-E2B-it-qat-UD-Q2_K_XL.gguf"}'

# Activate for serving
curl -X POST http://localhost:8000/api/v1/models/<model-id>/activate

# System info
curl http://localhost:8000/api/v1/system/info

# OpenAPI docs
open http://localhost:8000/docs
```

## Docker

```bash
cp .env.example .env
docker compose up -d
```

This builds a single container running both `llama-server` (port 8080) and `modelctl-api` (port 8000), mounts `registry/` and `storage/`, and serves the active model.

### Manage models via API

```bash
curl http://localhost:8000/api/v1/models
curl -X POST http://localhost:8000/api/v1/models/<id>/activate
```

### Manage models via CLI inside container

```bash
docker compose exec llama-server modelctl list
docker compose exec llama-server modelctl activate <model-id>
```

```bash
docker compose exec llama-server modelctl list
docker compose exec llama-server modelctl activate <model-id>
```

## Tests

```bash
uv run pytest tests/ -v
```
