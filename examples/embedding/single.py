"""
Single Text Embedding
=====================

Gets an embedding vector for one piece of text.

Embeddings convert text into a dense vector of floats that
captures semantic meaning. Useful for search, clustering,
and similarity comparisons.

Usage:
    uv run python examples/embedding/single.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - An embedding model installed and container started for \"embedding\"
      capability (e.g. nomic-ai/nomic-embed-text-v1.5-GGUF)

Network flow:
    Client -> nginx (:6060) -> modelctl-embedding:8080 -> llama.cpp server
"""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="sk-no-key-required",
)


def main() -> None:
    response = client.embeddings.create(
        model="local-model",
        input="Hello world, this is a test sentence.",
    )

    vector = response.data[0].embedding
    print(f"Vector dimension: {len(vector)}")
    print(f"First 5 values:   {vector[:5]}...")
    print(f"Total tokens:     {response.usage.total_tokens}")


if __name__ == "__main__":
    main()
