from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable


TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class HashEmbeddingProvider:
    """Deterministic, dependency-free dense vectors for the local baseline.

    This is deliberately small and replaceable. Production deployments can provide
    a code-trained embedding provider through the same ``embed`` interface.
    """

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = list(_tokens(text))
        for token in tokens:
            _add_feature(vector, f"word:{token}", 1.0)
            # Character n-grams make camelCase, snake_case, and natural-language
            # variations such as "refreshing" and "refresh_token" closer together.
            padded = f"^{token}$"
            for index in range(len(padded) - 2):
                _add_feature(vector, f"tri:{padded[index:index + 3]}", 0.25)
        return _normalise(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vectors must have the same dimensions.")
    return sum(a * b for a, b in zip(left, right, strict=True))


def _tokens(text: str) -> Iterable[str]:
    for token in TOKEN_PATTERN.findall(text):
        # Split identifiers so `refresh_access_token` can match "refresh token".
        words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token).replace("_", " ").lower()
        yield from words.split()


def _add_feature(vector: list[float], feature: str, weight: float) -> None:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    index = value % len(vector)
    vector[index] += weight if value & 1 else -weight


def _normalise(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]
