from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.repository import Repository
from app.db.models.repository_chunk import RepositoryChunk
from app.modules.chunks.schemas import RepositoryChunkRead
from app.modules.embeddings.service import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    GoogleEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.modules.repositories.service import RepositoryNotFoundError
from app.modules.retrieval.schemas import RepositorySearchResponse, RepositorySearchResult


class RepositoryRetrievalService:
    def __init__(self, settings: Settings, provider: EmbeddingProvider | None = None) -> None:
        self.settings = settings
        self.provider = provider

    async def search(
        self, session: AsyncSession, repository_id: UUID, owner_id: UUID, query: str,
        source_type: str | None, chunk_type: str | None, limit: int,
    ) -> RepositorySearchResponse:
        owner = await session.execute(select(Repository.id).where(
            Repository.id == repository_id, Repository.owner_id == owner_id
        ))
        if owner.scalar_one_or_none() is None:
            raise RepositoryNotFoundError

        vector = await self._query_vector(query)
        rows = await self._hybrid_rows(session, repository_id, query, source_type, chunk_type, limit, vector)
        chunk_ids = [row["chunk_id"] for row in rows]
        if not chunk_ids:
            return RepositorySearchResponse(repository_id=repository_id, query=query, results=[], vector_search_used=vector is not None)
        chunk_rows = await session.execute(select(RepositoryChunk).where(RepositoryChunk.id.in_(chunk_ids)))
        chunks = {chunk.id: RepositoryChunkRead.model_validate(chunk) for chunk in chunk_rows.scalars()}
        return RepositorySearchResponse(
            repository_id=repository_id, query=query, vector_search_used=vector is not None,
            results=[RepositorySearchResult(
                chunk=chunks[row["chunk_id"]], score=float(row["score"]),
                lexical_score=float(row["lexical_score"] or 0),
                vector_score=float(row["vector_score"]) if row["vector_score"] is not None else None,
            ) for row in rows if row["chunk_id"] in chunks],
        )

    async def _query_vector(self, query: str) -> list[float] | None:
        if self.provider is None and not self._configured_provider_key():
            return None
        provider = self.provider or self._provider()
        vector = (await provider.embed([query], task_type="RETRIEVAL_QUERY"))[0]
        if len(vector) != self.settings.embedding_dimensions:
            raise EmbeddingConfigurationError("Query embedding dimensions do not match configured storage.")
        return vector

    def _configured_provider_key(self) -> str | None:
        return self.settings.google_api_key if self.settings.embedding_provider == "google" else self.settings.openai_api_key

    def _provider(self) -> EmbeddingProvider:
        if self.settings.embedding_provider == "google":
            return GoogleEmbeddingProvider(
                self.settings.google_api_key or "", self.settings.embedding_model, self.settings.embedding_dimensions
            )
        return OpenAIEmbeddingProvider(
            self.settings.openai_api_key or "", self.settings.embedding_model, self.settings.embedding_dimensions
        )

    async def _hybrid_rows(self, session, repository_id, query, source_type, chunk_type, limit, vector):
        filters = "c.repository_id = :repository_id"
        params: dict[str, object] = {
            "repository_id": repository_id,
            "query": query,
            "limit": limit,
            "exact_titles": self._exact_symbol_titles(query),
        }
        if source_type:
            filters += " AND c.source_type = :source_type"
            params["source_type"] = source_type
        if chunk_type:
            filters += " AND c.chunk_type = :chunk_type"
            params["chunk_type"] = chunk_type
        if vector is None:
            statement = text(f"""
                WITH candidates AS (
                  SELECT c.id AS chunk_id,
                    ts_rank_cd(to_tsvector('simple', concat_ws(' ', c.title, c.content)), plainto_tsquery('simple', :query)) AS lexical_score,
                    CASE WHEN lower(c.title) = ANY(CAST(:exact_titles AS text[])) THEN 1.0 ELSE 0.0 END AS exact_title_score
                  FROM repository_chunks c
                  WHERE {filters}
                )
                SELECT chunk_id, lexical_score, NULL::float AS vector_score,
                       (lexical_score + exact_title_score) AS score
                FROM candidates
                WHERE lexical_score > 0 OR exact_title_score > 0
                ORDER BY score DESC, chunk_id
                LIMIT :limit
            """)
        else:
            params["query_vector"] = str(vector)
            statement = text(f"""
                WITH candidates AS (
                  SELECT c.id AS chunk_id,
                    ts_rank_cd(to_tsvector('simple', concat_ws(' ', c.title, c.content)), plainto_tsquery('simple', :query)) AS lexical_score,
                    CASE WHEN lower(c.title) = ANY(CAST(:exact_titles AS text[])) THEN 1.0 ELSE 0.0 END AS exact_title_score,
                    1 - (e.embedding <=> CAST(:query_vector AS vector)) AS vector_score
                  FROM repository_chunks c
                  LEFT JOIN repository_chunk_embeddings e
                    ON e.chunk_id = c.id AND e.model = :embedding_model
                  WHERE {filters}
                )
                SELECT chunk_id, lexical_score, vector_score,
                  (0.25 * lexical_score + 0.55 * COALESCE(vector_score, 0) + 0.40 * exact_title_score) AS score
                FROM candidates
                WHERE lexical_score > 0 OR vector_score IS NOT NULL OR exact_title_score > 0
                ORDER BY score DESC, chunk_id
                LIMIT :limit
            """)
            params["embedding_model"] = self.settings.embedding_model
        result = await session.execute(statement, params)
        return list(result.mappings())

    @staticmethod
    def _exact_symbol_titles(query: str) -> list[str]:
        """Find code-style identifiers that deserve an exact-title ranking boost."""
        terms = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", query)
        return list(dict.fromkeys(
            term.lower() for term in terms
            if "_" in term or any(character.isupper() for character in term[1:])
        ))
