"""
Controlled Chat Output
======================

Demonstrates using system prompts, temperature, and max_tokens
to control the model's behavior and output length.

- system prompt: sets the assistant's persona/style
- temperature:   higher (e.g. 0.8) = more creative, lower (0.1) = more deterministic
- max_tokens:    limits response length

Usage:
    uv run python examples/chat/controlled.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - A chat model installed and container started for \"chat\" capability
"""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="sk-no-key-required",
)


def main() -> None:
    response = client.chat.completions.create(
        model="local-model",
        messages=[
            {"role": "system",
             "content": "You are a poet. Always respond in rhyming couplets."},
            {"role": "user",
             "content": "Write a short poem about the ocean."},
        ],
        temperature=0.8,       # creative
        max_tokens=150,        # short response
        stream=False,
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
