"""
Embedding examples — use the nginx reverse proxy for embeddings.

All requests go through http://localhost:6060/v1 (nginx port).
Nginx routes /v1/embeddings to the modelctl-embedding container.

Prerequisites:
    - Docker containers running: docker compose up -d
    - An embedding model installed and container started for capability "embedding"
      (e.g. nomic-ai/nomic-embed-text-v1.5-GGUF)

Install the OpenAI client:
    pip install openai
"""

from openai import OpenAI
import numpy as np

client = OpenAI(
    base_url="http://localhost:6060/v1",  # nginx reverse proxy
    api_key="sk-no-key-required",
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Single text embedding
# ═══════════════════════════════════════════════════════════════════════

def embed_single(text: str) -> list[float]:
    """Get an embedding vector for a single text string."""
    response = client.embeddings.create(
        model="local-model",
        input=text,
    )
    return response.data[0].embedding


# ═══════════════════════════════════════════════════════════════════════
# 2. Batch embedding (multiple texts at once)
# ═══════════════════════════════════════════════════════════════════════

def embed_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts in a single request."""
    response = client.embeddings.create(
        model="local-model",
        input=texts,
    )
    # Sort by index to preserve input order
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in sorted_data]


# ═══════════════════════════════════════════════════════════════════════
# 3. Cosine similarity (semantic comparison)
# ═══════════════════════════════════════════════════════════════════════

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def semantic_similarity_demo() -> None:
    """Compare semantic similarity between phrases."""
    phrases = [
        "I love programming in Python",
        "Coding in Python is great",
        "I enjoy eating pizza",
    ]

    vectors = embed_batch(phrases)

    print(f"{'':20s} {'Python love':15s} {'Coding great':15s} {'Pizza enjoy':15s}")
    print("-" * 65)
    for i, phrase in enumerate(phrases):
        sims = [cosine_similarity(vectors[i], vectors[j])
                for j in range(len(phrases))]
        print(
            f"{phrase[:20]:20s} {sims[0]:.4f}         {sims[1]:.4f}         {sims[2]:.4f}")


# ═══════════════════════════════════════════════════════════════════════
# 4. Raw HTTP (without OpenAI client)
# ═══════════════════════════════════════════════════════════════════════

def raw_http_embedding() -> None:
    """Send an embedding request using plain curl."""
    import subprocess
    import json

    payload = json.dumps({
        "model": "local-model",
        "input": "Hello from curl",
    })

    result = subprocess.run(
        ["curl", "-s", "http://localhost:6060/v1/embeddings",
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    vec = data["data"][0]["embedding"]
    print(f"Vector dimension: {len(vec)}")
    print(f"First 5 values:   {vec[:5]}...")


# ═══════════════════════════════════════════════════════════════════════
# 5. Embedding info
# ═══════════════════════════════════════════════════════════════════════

def embedding_info() -> None:
    """Show embedding model metadata: dimension, usage stats."""
    response = client.embeddings.create(
        model="local-model",
        input="test",
    )
    vec = response.data[0].embedding
    usage = response.usage

    print(f"Vector dimension: {len(vec)}")
    print(f"Prompt tokens:    {usage.prompt_tokens}")
    print(f"Total tokens:     {usage.total_tokens}")


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║  Embedding Examples (via nginx :6060)       ║")
    print("╚══════════════════════════════════════════════╝\n")

    print("─── 1. Single text embedding ───")
    vec = embed_single("Hello world, this is a test.")
    print(f"Dimension: {len(vec)}")
    print(f"First 5 values: {vec[:5]}...\n")

    print("─── 2. Batch embedding (3 texts at once) ───")
    texts = ["first text", "second text", "third text"]
    vectors = embed_batch(texts)
    for i, v in enumerate(vectors):
        print(f"  Text {i+1}: dimension {len(v)}, first 3 values: {v[:3]}...")

    print("\n─── 3. Semantic similarity comparison ───")
    semantic_similarity_demo()

    print("\n─── 4. Raw HTTP (curl) ───")
    raw_http_embedding()

    print("\n─── 5. Embedding metadata ───")
    embedding_info()
