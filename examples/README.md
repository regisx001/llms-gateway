# Examples — Using the API via Nginx Reverse Proxy

Example scripts demonstrating how to use the llama.cpp inference API
through the nginx reverse proxy (port 6060) for chat and embeddings.

All requests flow through a single entry point:
```
Client -> nginx (:6060) -> modelctl-{capability}:8080 -> llama.cpp server
```

## Prerequisites

- Docker containers running: `docker compose up -d`
- A **chat** model installed and a container started for capability `chat`
- An **embedding** model installed and a container started for capability `embedding`
- Python 3.10+ with OpenAI client: `pip install openai numpy`

## Chat examples

Each file is self-contained with a docstring explaining the usage.

| File | Description |
|---|---|
| `chat/basic.py` | Single question-answer, non-streaming |
| `chat/streaming.py` | Token-by-token streaming response |
| `chat/multi_turn.py` | Conversation with history across multiple turns |
| `chat/controlled.py` | System prompt, temperature, max_tokens control |
| `chat/raw_http.py` | Plain curl request (no Python client) |
| `chat/raw_streaming.py` | Streaming via raw curl with SSE |

```bash
uv run python examples/chat/basic.py
uv run python examples/chat/streaming.py
uv run python examples/chat/multi_turn.py
uv run python examples/chat/controlled.py
uv run python examples/chat/raw_http.py
uv run python examples/chat/raw_streaming.py
```

## Embedding examples

| File | Description |
|---|---|
| `embedding/single.py` | Embedding for one text string |
| `embedding/batch.py` | Embedding for multiple texts in one request |
| `embedding/similarity.py` | Cosine similarity matrix between phrases |
| `embedding/raw_http.py` | Plain curl request (no Python client) |

```bash
uv run python examples/embedding/single.py
uv run python examples/embedding/batch.py
uv run python examples/embedding/similarity.py
uv run python examples/embedding/raw_http.py
```

## Orchestration lifecycle demo

```bash
uv run python examples/run_llama_with_orchestrator.py --dry-run
```

## Quick curl reference

### Chat

```bash
# Basic (non-streaming)
curl -s http://localhost:6060/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","messages":[{"role":"user","content":"Hello"}],"stream":false}'

# Streaming
curl -s -N http://localhost:6060/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","messages":[{"role":"user","content":"Count to 5"}],"stream":true}'

# With system prompt + temperature
curl -s http://localhost:6060/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","messages":[{"role":"system","content":"You are a poet"},{"role":"user","content":"Write about the moon"}],"temperature":0.8,"max_tokens":200}'
```

### Embedding

```bash
# Single text
curl -s http://localhost:6060/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","input":"Hello world"}'

# Batch (multiple texts)
curl -s http://localhost:6060/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"local-model","input":["first text","second text","third text"]}'
```
