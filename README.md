# LLMs Gateway

LLM inference gateway with model management — search, download, and serve GGUF models via `llama.cpp`.

## Anatomy

```
.
├── apps/modelctl          # CLI app (modelctl command)
│   └── src/modelctl/cli.py
├── libs/modelctl-core     # core library
│   └── src/modelctl_core/
│       ├── models.py      # data classes (Model, Artifact, Download)
│       ├── registry.py    # JSON file persistence
│       ├── huggingface.py # HuggingFace API client
│       └── validator.py   # file validation
├── registry/              # JSON files tracking models & downloads
├── storage/               # downloaded model files
├── tests/                 # pytest test suite
├── pyproject.toml         # uv workspace root
├── docker-compose.yml     # runs llama-server + modelctl
├── Dockerfile.llamacpp.server
└── entrypoint.sh          # container startup script
```

## Setup

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install everything
uv sync
```

## Usage

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

## Docker

```bash
cp .env.example .env
docker compose up -d
```

This builds a container with `llama-server` + `modelctl`, mounts `registry/` and `storage/`, and serves the active model on port `9999` (configurable in `.env`).

Switch models at runtime:

```bash
docker compose exec llama-server modelctl list
docker compose exec llama-server modelctl activate <model-id>
```

## Tests

```bash
uv run pytest tests/ -v
```
