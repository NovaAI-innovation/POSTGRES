from __future__ import annotations

import hashlib


class EmbeddingService:
    def __init__(self, model_name: str, dimensions: int = 384) -> None:
        self.model_name = model_name
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector: list[float] = []
        for idx in range(self.dimensions):
            digest = hashlib.sha256(f"{idx}:{text}".encode("utf-8")).digest()
            value = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
            vector.append((value * 2.0) - 1.0)
        return vector

    def validate(self, vector: list[float]) -> bool:
        return len(vector) == self.dimensions
