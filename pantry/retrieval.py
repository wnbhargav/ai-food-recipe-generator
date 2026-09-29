import math
import re
from collections import Counter

from pantry.models import Context


def cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("Embedding dimensions do not match")
    if not all(math.isfinite(x) for x in left + right):
        raise ValueError("Embedding contains non-finite values")
    denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def keyword_vectors(texts: list[str]) -> list[list[float]]:
    counts = [Counter(re.findall(r"[a-z]+", text.lower())) for text in texts]
    vocabulary = sorted(set().union(*(count.keys() for count in counts)))
    return [[float(count[word]) for word in vocabulary] for count in counts]


def rank(documents, vectors, query_vector, limit=3) -> list[Context]:
    if len(documents) != len(vectors):
        raise ValueError("Missing document embeddings")
    scored = [
        Context(**document, score=round(cosine(vector, query_vector), 4))
        for document, vector in zip(documents, vectors)
    ]
    return sorted(scored, key=lambda item: (-item.score, item.id))[:limit]
