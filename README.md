# LLMs Gateway

LLM inference gateway with model management — search, download, and serve GGUF models via `llama.cpp`.

## Architecture

```
[Client] → :6060 → Nginx (reverse proxy)
                      ├─ /v1/chat/completions  → modelctl-chat:8080   (internal)
                      ├─ /v1/embeddings        → modelctl-embedding:8080
                      ├─ /v1/rerank            → modelctl-reranker:8080
                      ├─ /v1/vision            → modelctl-vision:8080
                      ├─ /v1/experimental      → modelctl-experimental:8080
                      └─ / (UI + Management)   → modelctl-api:8000
```

Nginx is the **single entry point**. Inference ports are never exposed to the host — all traffic routes through Nginx on the internal `modelctl-net` Docker network.

Each model capability (chat, embedding, reranker, vision, experimental) runs in its **own dedicated `llama-server` container**, managed dynamically via the Docker SDK.

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
├── libs/
│   ├── modelctl-core         # core library (registry, huggingface, validation)
│   │   └── src/modelctl_core/
│   │       ├── models.py     # data classes (Model, Artifact, Download)
│   │       ├── registry.py   # JSON file persistence
│   │       ├── _locations.py # path resolution for dev vs Docker
│   │       ├── huggingface.py# HuggingFace API client
│   │       └── validator.py  # file validation
│   └── modelctl-orch         # container orchestration (lifecycle, port allocator)
│       └── src/modelctl_orch/
│           ├── container_manager.py  # Docker SDK wrapper
│           ├── lifecycle.py          # state machine
│           ├── models.py             # orchestration schemas
│           └── port_allocator.py     # internal port tracking
├── registry/                 # [dev] JSON files tracking models & downloads
├── storage/                  # [dev] downloaded model files
├── nginx.conf                # reverse proxy configuration
├── docker-compose.yml        # runs nginx + llama-server + modelctl-api
├── Dockerfile.llamacpp.server
└── entrypoint.sh             # container startup (starts modelctl-api only)
```

## Path Separation

The application supports two independent modes with separate storage paths:

| Mode | Registry | Storage | How |
|---|---|---|---|
| **Dev** (native) | `./registry/` | `./storage/` | Tree-walk from package root |
| **Docker** | `~/LLMGateway-Models/registry` | `~/LLMGateway-Models/storage` | Env vars in `docker-compose.yml` |

Models installed in one mode are **not** visible in the other. Inference containers always use the Docker path.

## Setup

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install everything
uv sync
```

## Usage

### Dev mode (native, no Docker)

```bash
# Start dev server
uv run uvicorn modelctl_api.main:app --reload --port 8000

# Health check
curl http://localhost:8000/health

# Install a model
curl -X POST http://localhost:8000/api/v1/models/install \
  -H "Content-Type: application/json" \
  -d '{"repo_id": "nomic-ai/nomic-embed-text-v1.5-GGUF", "filename": "nomic-embed-text-v1.5.Q4_K_M.gguf", "model_type": "embedding"}'

# List models
curl http://localhost:8000/api/v1/models

# Search HuggingFace
curl "http://localhost:8000/api/v1/search?q=llama&limit=5"

# OpenAPI docs
open http://localhost:8000/docs
```

### Docker mode

```bash
cp .env.example .env
docker compose up -d
```

All requests go through **Nginx on port 6060**:

```bash
# Web UI
open http://localhost:6060

# Install a model
curl -X POST http://localhost:6060/api/v1/models/install \
  -H "Content-Type: application/json" \
  -d '{"repo_id": "nomic-ai/nomic-embed-text-v1.5-GGUF", "filename": "nomic-embed-text-v1.5.Q4_K_M.gguf", "model_type": "embedding"}'

# Start an inference container
curl -X POST http://localhost:6060/api/v1/containers \
  -H "Content-Type: application/json" \
  -d '{"capability": "chat", "model_id": "<model-id>"}'

# Chat (via Nginx → modelctl-chat container)
curl http://localhost:6060/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","messages":[{"role":"user","content":"Hello"}],"stream":false}'

# Embedding (via Nginx → modelctl-embedding container)
curl http://localhost:6060/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","input":"Hello world"}'

# System info
curl http://localhost:6060/api/v1/system/info
```

You can also access the API directly (bypassing Nginx) on port 8000.

## Nginx Reverse Proxy

### Routing table

| URL | Backend | Purpose |
|---|---|---|
| `/v1/chat/completions` | `modelctl-chat:8080` | Chat inference |
| `/v1/embeddings` | `modelctl-embedding:8080` | Embedding inference |
| `/v1/rerank` | `modelctl-reranker:8080` | Reranker |
| `/v1/vision` | `modelctl-vision:8080` | Vision |
| `/v1/experimental` | `modelctl-experimental:8080` | Experimental |
| `/api/v1/*` | `modelctl-api:8000` | Management API |
| `/` | `modelctl-api:8000` | Web UI (SPA) |

### Key design decisions

- **Variable-based `proxy_pass`**: hostnames resolved at request-time via Docker DNS (`127.0.0.11`), not at startup — Nginx boots before inference containers exist
- **Fixed container names**: containers are named `modelctl-{capability}` — the Nginx config is static and never needs reloading
- **Streaming support**: `proxy_buffering off`, `proxy_cache off` for SSE chat streaming
- **600s timeouts**: for long-running inference

## Per-Capability Container Architecture

Each model type gets its **own dedicated `llama-server` inference container** managed via the `modelctl-orch` library.

### Container naming

Containers use **fixed names** for Nginx routing: `modelctl-chat`, `modelctl-embedding`, etc. Starting a new model for the same capability **replaces** the existing container automatically.

### Lifecycle State Machine

```
stopped ──► starting ──► running ──► stopping ──► stopped
                │                        │
                └──► failed ◄────────────┘
                      │
                      └──► starting (retry)
```

### Manage containers via API

```bash
# Start a container
curl -X POST http://localhost:6060/api/v1/containers \
  -H "Content-Type: application/json" \
  -d '{"capability": "chat", "model_id": "<model-id>"}'

# List all
curl http://localhost:6060/api/v1/containers

# Inspect
curl http://localhost:6060/api/v1/containers/<container-id>

# Logs
curl http://localhost:6060/api/v1/containers/<container-id>/logs?tail=100

# Stop & remove
curl -X DELETE http://localhost:6060/api/v1/containers/<container-id>
```

### Manage via CLI inside container

```bash
docker compose exec llama-server modelctl list
docker compose exec llama-server modelctl install <repo-id> <filename>
```

## Environment variables

See `.env.example`:

```
LLAMACPP_IMAGE=ghcr.io/ggml-org/llama.cpp:server
NGINX_PORT=6060
MODELCTL_API_PORT=8000
MODELCTL_NETWORK=modelctl-net
```

## Tests

```bash
# All tests
uv run pytest libs/modelctl-core/tests/ libs/modelctl-orch/tests/ apps/modelctl-api/tests/ -v

# Or via Makefile
make test
```
