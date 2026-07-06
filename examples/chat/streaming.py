"""
Streaming Chat Completion
=========================

Sends a chat message and prints tokens as they arrive (SSE stream).

Streaming gives a real-time experience — useful for chat UIs
where you want to show the response incrementally.

Usage:
    uv run python examples/chat/streaming.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - A chat model installed and container started for \"chat\" capability

Network flow:
    Client -> nginx (:6060) -> modelctl-chat:8080 -> llama.cpp server
"""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="sk-no-key-required",
)


def main() -> None:
    stream = client.chat.completions.create(
        model="local-model",
        messages=[
            {"role": "user", "content": "Tell me a fun fact about octopuses."},
        ],
        stream=True,                    # receive tokens incrementally
    )

    print("Answer: ", end="", flush=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()  # final newline


if __name__ == "__main__":
    main()
