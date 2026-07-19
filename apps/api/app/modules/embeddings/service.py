from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.repository_chunk import RepositoryChunk
from app.db.models.repository_chunk_embedding import RepositoryChunkEmbedding


class EmbeddingConfigurationError(RuntimeError):
    pass


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    async def embed(self, inputs: Sequence[str], task_type: str | None = None) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
    """Small provider boundary that keeps credentials out of jobs and persistence."""

    def __init__(self, api_key: str, model: str, dimensions: int) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions

    async def embed(self, inputs: Sequence[str], task_type: str | None = None) -> list[list[float]]:
        del task_type
        payload: dict[str, object] = {"model": self.model, "input": list(inputs)}
        # OpenAI's v3 embedding models accept a dimensions override; older models do not.
        if self.model.startswith("text-embedding-3"):
            payload["dimensions"] = self.dimensions
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError("Embedding provider request failed.") from exc
        data = response.json().get("data", [])
        vectors = [item.get("embedding") for item in data]
        if len(vectors) != len(inputs) or any(not isinstance(vector, list) for vector in vectors):
            raise EmbeddingProviderError("Embedding provider returned an invalid response.")
        return vectors


class GoogleEmbeddingProvider:
    """Gemini text embedding client using the Google AI Studio REST API."""

    def __init__(self, api_key: str, model: str, dimensions: int) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions

    async def embed(self, inputs: Sequence[str], task_type: str | None = None) -> list[list[float]]:
        vectors: list[list[float]] = []
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                for input_text in inputs:
                    payload: dict[str, object] = {
                        "model": f"models/{self.model}",
                        "content": {"parts": [{"text": input_text}]},
                        "outputDimensionality": self.dimensions,
                    }
                    if task_type:
                        payload["taskType"] = task_type
                    response = await client.post(
                        endpoint,
                        headers={"x-goog-api-key": self.api_key},
                        json=payload,
                    )
                    response.raise_for_status()
                    vector = response.json().get("embedding", {}).get("values")
                    if not isinstance(vector, list):
                        raise EmbeddingProviderError("Google embedding provider returned an invalid response.")
                    vectors.append(vector)
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError("Google embedding provider request failed.") from exc
        return vectors


@dataclass(frozen=True)
class EmbeddingRunResult:
    embedded: int
    skipped: int


class RepositoryChunkEmbeddingService:
    def __init__(self, settings: Settings, provider: EmbeddingProvider | None = None) -> None:
        self.settings = settings
        self.provider = provider

    @staticmethod
    def source_text(chunk: RepositoryChunk) -> str:
        return f"{chunk.title}\n\n{chunk.content}"

    @staticmethod
    def source_hash(chunk: RepositoryChunk) -> str:
        return hashlib.sha256(RepositoryChunkEmbeddingService.source_text(chunk).encode("utf-8")).hexdigest()

    def _provider(self) -> EmbeddingProvider:
        if self.provider is not None:
            return self.provider
        if self.settings.embedding_provider == "google":
            if not self.settings.google_api_key:
                raise EmbeddingConfigurationError("GOOGLE_API_KEY is required to generate Gemini embeddings.")
            return GoogleEmbeddingProvider(
                self.settings.google_api_key,
                self.settings.embedding_model,
                self.settings.embedding_dimensions,
            )
        if not self.settings.openai_api_key:
            raise EmbeddingConfigurationError("OPENAI_API_KEY is required to generate OpenAI embeddings.")
        return OpenAIEmbeddingProvider(self.settings.openai_api_key, self.settings.embedding_model, self.settings.embedding_dimensions)

    async def embed_repository_chunks(self, session: AsyncSession, repository_id: UUID) -> EmbeddingRunResult:
        """Embed only persisted chunks and safely skip an unchanged chunk/model pair."""
        chunks_result = await session.execute(
            select(RepositoryChunk)
            .where(RepositoryChunk.repository_id == repository_id)
            .order_by(RepositoryChunk.path, RepositoryChunk.start_line, RepositoryChunk.id)
        )
        chunks = list(chunks_result.scalars())
        existing_result = await session.execute(
            select(RepositoryChunkEmbedding).where(
                RepositoryChunkEmbedding.repository_id == repository_id,
                RepositoryChunkEmbedding.model == self.settings.embedding_model,
            )
        )
        existing = {embedding.chunk_id: embedding for embedding in existing_result.scalars()}
        pending = [
            chunk for chunk in chunks
            if (saved := existing.get(chunk.id)) is None
            or saved.source_hash != self.source_hash(chunk)
            or saved.dimensions != self.settings.embedding_dimensions
        ]
        if not pending:
            return EmbeddingRunResult(embedded=0, skipped=len(chunks))

        provider = self._provider()
        embedded = 0
        for start in range(0, len(pending), self.settings.embedding_batch_size):
            batch = pending[start : start + self.settings.embedding_batch_size]
            vectors = await provider.embed([self.source_text(chunk) for chunk in batch], task_type="RETRIEVAL_DOCUMENT")
            for chunk, vector in zip(batch, vectors, strict=True):
                if len(vector) != self.settings.embedding_dimensions:
                    raise EmbeddingProviderError("Embedding provider returned an unexpected vector dimension.")
                saved = existing.get(chunk.id)
                if saved is None:
                    session.add(RepositoryChunkEmbedding(
                        repository_id=repository_id,
                        chunk_id=chunk.id,
                        source_hash=self.source_hash(chunk),
                        model=self.settings.embedding_model,
                        dimensions=len(vector),
                        embedding=vector,
                    ))
                else:
                    saved.source_hash = self.source_hash(chunk)
                    saved.dimensions = len(vector)
                    saved.embedding = vector
                embedded += 1
        await session.commit()
        return EmbeddingRunResult(embedded=embedded, skipped=len(chunks) - embedded)
