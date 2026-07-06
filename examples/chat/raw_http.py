"""
Chat via Raw HTTP (curl)
========================

Sends a chat completion request using a plain HTTP call
(subprocess calling curl). Useful for shell scripting and
integration testing without Python dependencies.

Usage:
    uv run python examples/chat/raw_http.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - A chat model installed and container started for \"chat\" capability
"""

import subprocess
import json


def main() -> None:
    payload = json.dumps({
        "model": "local-model",
        "messages": [{"role": "user", "content": "Say hello in German."}],
        "stream": False,
    })

    result = subprocess.run(
        [
            "curl", "-s",
            "http://localhost:6060/v1/chat/completions",
            "-H", "Content-Type: application/json",
            "-d", payload,
        ],
        capture_output=True, text=True,
    )

    data = json.loads(result.stdout)
    print(data["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
