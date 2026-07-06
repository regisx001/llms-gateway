"""
Streaming Chat via Raw HTTP (SSE)
==================================

Sends a streaming chat request using curl with -N (no-buffer) flag
to display the raw Server-Sent Events stream in real-time.

This is the same protocol used by the OpenAI Python client under the hood.

Usage:
    uv run python examples/chat/raw_streaming.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - A chat model installed and container started for \"chat\" capability
"""

import subprocess
import json


def main() -> None:
    payload = json.dumps({
        "model": "local-model",
        "messages": [{"role": "user", "content": "Count from 1 to 10."}],
        "stream": True,
    })

    subprocess.run(
        [
            "curl", "-s", "-N",
            "http://localhost:6060/v1/chat/completions",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
    )


if __name__ == "__main__":
    main()
