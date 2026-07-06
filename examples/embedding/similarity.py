"""
Cosine Similarity (Semantic Comparison)
========================================

Computes cosine similarity between embedding vectors to
measure how semantically related two texts are.

Values range from -1 (opposite meaning) to 1 (identical meaning).
Related concepts score higher than unrelated ones.

Usage:
    uv run python examples/embedding/similarity.py

Prerequisites:
    - Docker containers running: docker compose up -d
    - An embedding model installed and container started for \"embedding\"
      capability (e.g. nomic-ai/nomic-embed-text-v1.5-GGUF)
    - numpy installed: pip install numpy
"""

from openai import OpenAI
import numpy as np

client = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="sk-no-key-required",
)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def main() -> None:
    phrases = [
        "I love programming in Python",
        "Coding in Python is great fun",
        "I enjoy eating pizza for dinner",
    ]

    # Batch-embed all phrases
    response = client.embeddings.create(
        model="local-model",
        input=phrases,
    )
    sorted_data = sorted(response.data, key=lambda x: x.index)
    vectors = [item.embedding for item in sorted_data]

    # Print similarity matrix
    print("Similarity matrix:\n")
    print(f"{'':25s} {'Python':12s} {'Coding':12s} {'Pizza':12s}")
    print("-" * 61)
    for i, phrase in enumerate(phrases):
        sims = [cosine_similarity(vectors[i], vectors[j]) for j in range(3)]
        print(
            f"{phrase[:25]:25s} {sims[0]:.4f}     {sims[1]:.4f}     {sims[2]:.4f}")

    print("\nNote: Python/Coding are similar (same topic), Pizza is different.")


if __name__ == "__main__":
    main()
