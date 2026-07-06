"""
Embedding via Raw HTTP (curl)
=============================

Sends an embedding request using a plain HTTP call
(subprocess calling curl). Useful for shell scripting and
integration testing without Python dependencies.

Usage:
    uv run python examples/embedding/raw_http.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - An embedding model installed and container started for \"embedding\"
      capability (e.g. nomic-ai/nomic-embed-text-v1.5-GGUF)
"""

import subprocess
import json


def main() -> None:
    payload = json.dumps({
        "model": "local-model",
        "input": "Hello from curl",
    })

    result = subprocess.run(
        [
            "curl", "-s",
            "http://localhost:6060/v1/embeddings",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
        capture_output=True, text=True,
    )

    data = json.loads(result.stdout)
    vec = data["data"][0]["embedding"]
    print(f"Vector dimension: {len(vec)}")
    print(f"First 5 values:   {vec[:5]}...")


if __name__ == "__main__":
    main()
