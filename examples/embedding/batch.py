"""
Batch Embedding
===============

Gets embeddings for multiple texts in a single request.

Batching is more efficient than sending separate requests
because the model processes all texts together.

Usage:
    uv run python examples/embedding/batch.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - An embedding model installed and container started for \"embedding\"
      capability (e.g. nomic-ai/nomic-embed-text-v1.5-GGUF)
"""

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="sk-no-key-required",
)


def main() -> None:
    texts = [
        "The quick brown fox jumps over the lazy dog",
        "Python is a powerful programming language",
        "Embeddings capture semantic meaning of text",
    ]

    response = client.embeddings.create(
        model="local-model",
        input=texts,                    # list of strings = batch request
    )

    # Sort by index to preserve input order
    sorted_data = sorted(response.data, key=lambda x: x.index)

    for i, item in enumerate(sorted_data):
        vec = item.embedding
        print(
            f"Text {i+1}: dimension {len(vec)}, first 3 values: {vec[:3]}...")


if __name__ == "__main__":
    main()
