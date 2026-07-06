"""
Basic Chat Completion (Non-Streaming)
======================================

Sends a single chat message and waits for the full response.

This is the simplest way to interact with the model —
useful when you want the complete answer at once.

Usage:
    uv run python examples/chat/basic.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - A chat model installed and container started for \"chat\" capability

Network flow:
    Client -> nginx (:6060) -> modelctl-chat:8080 -> llama.cpp server
"""

from openai import OpenAI

# The nginx reverse proxy is the single entry point.
# It routes /v1/chat/completions to the modelctl-chat container.
client = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="sk-no-key-required",
)


def main() -> None:
    response = client.chat.completions.create(
        model="local-model",            # ignored by llama.cpp, required by client
        messages=[
            {"role": "user", "content": "What is the capital of France?"},
        ],
        stream=False,                   # wait for the full response
    )

    answer = response.choices[0].message.content
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
