# Examples — modelctl-orch Programmatic Usage

Example scripts demonstrating how to use the `modelctl-orch` library
programmatically to manage llama.cpp inference containers.

## Prerequisites

- Docker daemon running (for container orchestration examples)
- The `llamaserver:latest` image built, or `LLAMACPP_IMAGE` env var set
- Python 3.10+ with `modelctl-orch` installed (`uv sync` from repo root)

## Scripts

| Script | Description |
|---|---|
| `run_llama_with_orchestrator.py` | Full lifecycle demo — allocates a port, starts a chat container, inspects it, fetches logs, then stops it. All steps are logged to `examples/orchestrator_run_*.log`. |

## Usage

```bash
# From repo root
uv run python examples/run_llama_with_orchestrator.py

# Or with a custom inference image
LLAMACPP_IMAGE=my-custom-image:latest uv run python examples/run_llama_with_orchestrator.py

# Dry-run mode (no Docker interaction)
uv run python examples/run_llama_with_orchestrator.py --dry-run
```

## Output

Each run writes a timestamped log file:

```
examples/orchestrator_run_20260702_120000.log
```

The log records every orchestrator call — model resolution, port
allocation, container start, health check, inference probe, and
teardown — with timing and status at each step.
