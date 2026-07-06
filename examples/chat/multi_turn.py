"""
Multi-Turn Conversation
=======================

Maintains conversation context across multiple turns by
building up a message history list.

Each call appends the assistant's reply to the history,
then the next user message continues the thread.

Usage:
    uv run python examples/chat/multi_turn.py

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
    # Start with a system prompt and the first user message
    messages = [
        {"role": "system", "content": "You are a concise travel guide."},
        {"role": "user",      "content": "What's the capital of Morocco?"},
    ]

    # --- Turn 1 ---
    reply = client.chat.completions.create(
        model="local-model", messages=messages, stream=False,
    ).choices[0].message.content
    print(f"User:      What's the capital of Morocco?")
    print(f"Assistant: {reply}\n")

    # Append the reply and add the next question
    messages.append({"role": "assistant", "content": reply})
    messages.append(
        {"role": "user",      "content": "What is its population?"})

    # --- Turn 2 ---
    reply = client.chat.completions.create(
        model="local-model", messages=messages, stream=False,
    ).choices[0].message.content
    print(f"User:      What is its population?")
    print(f"Assistant: {reply}")


if __name__ == "__main__":
    main()
