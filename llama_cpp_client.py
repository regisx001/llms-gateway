"""
Simple client for the llama.cpp server's inference API.

Prerequisites:
    1. Start the server first, e.g.:
         llama-server -m model.gguf --port 8080
       or pull a model directly:
         llama-server -hf ggml-org/gemma-3-1b-it-GGUF

    2. Install the OpenAI client:
         pip install openai --break-system-packages
"""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",  # nginx reverse proxy
    api_key="sk-no-key-required",  # llama-server ignores this unless --api-key was set
)


def chat(prompt: str, stream: bool = True) -> None:
    """Send a chat message and print the response (streaming by default)."""
    response = client.chat.completions.create(
        model="local-model",  # ignored by llama-server, required by the client lib
        messages=[{"role": "user", "content": prompt}],
        stream=stream,
    )

    if stream:
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)
        print()  # newline at the end
    else:
        print(response.choices[0].message.content)


def chat_with_history(messages: list[dict]) -> str:
    """Send a full conversation (list of {"role", "content"} dicts) and return the reply."""
    response = client.chat.completions.create(
        model="local-model",
        messages=messages,
    )
    return response.choices[0].message.content


def embed(text: str) -> list[float]:
    """Get an embedding vector for a piece of text."""
    response = client.embeddings.create(
        model="local-model",
        input=text,
    )
    return response.data[0].embedding


if __name__ == "__main__":
    print("--- Streaming chat ---")
    chat("Give me one fun fact about Tangier.")

    print("\n--- Multi-turn conversation ---")
    history = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "What's the capital of Morocco?"},
    ]
    reply = chat_with_history(history)
    print(reply)

    history.append({"role": "assistant", "content": reply})
    history.append({"role": "user", "content": "And its population?"})
    print(chat_with_history(history))

    # Uncomment if your loaded model supports embeddings:
    # print("\n--- Embedding ---")
    # vec = embed("hello world")
    # print(f"Embedding length: {len(vec)}")
