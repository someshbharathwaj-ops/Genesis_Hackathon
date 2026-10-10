"""Configurable embedding generation supporting deterministic offline mocks and live adapters."""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class BaseEmbeddingProvider(ABC):
    """Abstract interface for dense vector embedding generation."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of passages."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generate vector embedding for a single search query."""
        pass


class DeterministicMockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, offline vector generator using word n-grams and locality hashing.

    Produces reproducible, unit-normalized 128-dimensional vectors. Texts sharing
    common domain terminology naturally exhibit high cosine similarity without any
    external network dependencies.
    """

    DIMENSION: int = 128

    def _generate_vector(self, text: str) -> list[float]:
        if not text.strip():
            # Zero vector fallback
            return [0.0] * self.DIMENSION

        vec = [0.0] * self.DIMENSION
        # Tokenize into clean lowercase words and 3-grams
        words = re.findall(r"\b\w+\b", text.lower())
        tokens = list(words)
        # Add character 3-grams for subword matching
        cleaned = re.sub(r"\s+", " ", text.lower())
        for i in range(len(cleaned) - 2):
            tokens.append(cleaned[i : i + 3])

        if not tokens:
            return [0.0] * self.DIMENSION

        for token in tokens:
            # Deterministic MD5 hash to bucket and sign
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            bucket = h % self.DIMENSION
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[bucket] += sign

        # L2 normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [round(x / norm, 6) for x in vec]
        else:
            vec = [0.0] * self.DIMENSION

        return vec

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._generate_vector(query)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Live Ollama embedding client with fallback to deterministic mock."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float = 15.0,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.timeout_seconds = timeout_seconds
        self._fallback_provider = DeterministicMockEmbeddingProvider()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for text in texts:
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model_name, "prompt": text},
                    )
                    if resp.status_code == 200:
                        data: dict[str, Any] = resp.json()
                        emb = data.get("embedding", [])
                        if emb and isinstance(emb, list):
                            results.append([float(x) for x in emb])
                            continue
                except Exception:
                    pass
                # Fallback to deterministic mock if live service is unavailable
                mock_emb = await self._fallback_provider.embed_query(text)
                results.append(mock_emb)
        return results

    async def embed_query(self, query: str) -> list[float]:
        res = await self.embed_texts([query])
        return res[0]


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory returning active embedding provider based on environment config."""
    if settings.USE_MOCK_LLM:
        return DeterministicMockEmbeddingProvider()
    return OllamaEmbeddingProvider()
