"""
Chat examples — use the nginx reverse proxy for chat completions.

All requests go through http://localhost:6060/v1 (nginx port).
Nginx routes /v1/chat/completions to the modelctl-chat container.

Prerequisites:
    - Docker containers running: docker compose up -d
    - A chat model installed and container started for capability "chat"

Install the OpenAI client:
    pip install openai
"""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:6060/v1",  # nginx reverse proxy
    api_key="sk-no-key-required",
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Basic chat (non-streaming)
# ═══════════════════════════════════════════════════════════════════════

def basic_chat() -> str:
    """Simple question-answer, returns the full response at once."""
    response = client.chat.completions.create(
        model="local-model",
        messages=[{"role": "user", "content": "What is the capital of Japan?"}],
        stream=False,
    )
    return response.choices[0].message.content


# ═══════════════════════════════════════════════════════════════════════
# 2. Streaming chat (token-by-token)
# ═══════════════════════════════════════════════════════════════════════

def streaming_chat(prompt: str) -> None:
    """Stream tokens as they arrive — good for real-time UX."""
    stream = client.chat.completions.create(
        model="local-model",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()


# ═══════════════════════════════════════════════════════════════════════
# 3. Multi-turn conversation with history
# ═══════════════════════════════════════════════════════════════════════

def multi_turn_chat() -> None:
    """Maintain conversation context across multiple turns."""
    messages = [
        {"role": "system", "content": "You are a helpful travel guide."},
        {"role": "user", "content": "What's the capital of Morocco?"},
    ]

    # Turn 1
    reply = client.chat.completions.create(
        model="local-model", messages=messages, stream=False,
    ).choices[0].message.content
    print(f"User: What's the capital of Morocco?")
    print(f"Assistant: {reply}\n")

    messages.append({"role": "assistant", "content": reply})
    messages.append({"role": "user", "content": "What is its population?"})

    # Turn 2
    reply = client.chat.completions.create(
        model="local-model", messages=messages, stream=False,
    ).choices[0].message.content
    print(f"User: What is its population?")
    print(f"Assistant: {reply}\n")


# ═══════════════════════════════════════════════════════════════════════
# 4. Chat with system prompt + temperature
# ═══════════════════════════════════════════════════════════════════════

def controlled_chat() -> str:
    """Use system prompt and temperature for controlled output."""
    response = client.chat.completions.create(
        model="local-model",
        messages=[
            {"role": "system",
                "content": "You are a poet. Always respond in rhyming couplets."},
            {"role": "user", "content": "Tell me about the ocean."},
        ],
        temperature=0.8,
        max_tokens=200,
        stream=False,
    )
    return response.choices[0].message.content


# ═══════════════════════════════════════════════════════════════════════
# 5. Raw HTTP (without OpenAI client)
# ═══════════════════════════════════════════════════════════════════════

def raw_http_chat() -> None:
    """Send a chat request using plain curl — useful for scripting."""
    import subprocess
    import json

    payload = json.dumps({
        "model": "local-model",
        "messages": [{"role": "user", "content": "Say hello in French."}],
        "stream": False,
    })

    result = subprocess.run(
        ["curl", "-s", "http://localhost:6060/v1/chat/completions",
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    print(data["choices"][0]["message"]["content"])


# ═══════════════════════════════════════════════════════════════════════
# 6. Streaming via raw HTTP (SSE)
# ═══════════════════════════════════════════════════════════════════════

def raw_streaming_chat() -> None:
    """Stream via curl — shows the raw SSE event stream."""
    import subprocess
    import json

    payload = json.dumps({
        "model": "local-model",
        "messages": [{"role": "user", "content": "Count from 1 to 5."}],
        "stream": True,
    })

    subprocess.run(
        ["curl", "-s", "-N", "http://localhost:6060/v1/chat/completions",
         "-H", "Content-Type: application/json",
         "-d", payload],
    )


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║  Chat Completion Examples (via nginx :6060) ║")
    print("╚══════════════════════════════════════════════╝\n")

    print("─── 1. Basic chat ───")
    print(basic_chat())

    print("\n─── 2. Streaming chat ───")
    streaming_chat("What is the tallest mountain on Earth?")

    print("\n─── 3. Multi-turn conversation ───")
    multi_turn_chat()

    print("\n─── 4. Controlled output (system prompt + temperature) ───")
    print(controlled_chat())

    print("\n─── 5. Raw HTTP (curl) ───")
    raw_http_chat()
