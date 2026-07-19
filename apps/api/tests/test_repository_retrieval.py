from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.modules.chunks.schemas import RepositoryChunkRead
from app.modules.embeddings.service import EmbeddingProviderError, RepositoryChunkEmbeddingService
from app.modules.repositories.service import RepositoryNotFoundError
from app.modules.retrieval.router import search_repository
from app.modules.retrieval.schemas import RepositorySearchResponse, RepositorySearchResult
from app.modules.retrieval.service import RepositoryRetrievalService


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000002")


def test_embedding_hash_tracks_the_searchable_chunk_content() -> None:
    first = SimpleNamespace(title="authenticate", content="validate the JWT")
    changed = SimpleNamespace(title="authenticate", content="validate the session cookie")

    assert RepositoryChunkEmbeddingService.source_hash(first) != RepositoryChunkEmbeddingService.source_hash(changed)
    assert RepositoryChunkEmbeddingService.source_text(first) == "authenticate\n\nvalidate the JWT"


def test_embedding_text_truncates_only_the_provider_input() -> None:
    chunk = SimpleNamespace(title="large", content="x" * 12_100)

    embedding_text = RepositoryChunkEmbeddingService.embedding_text(chunk)

    assert len(embedding_text) == RepositoryChunkEmbeddingService.MAX_EMBEDDING_INPUT_CHARACTERS
    assert embedding_text.endswith(RepositoryChunkEmbeddingService.TRUNCATION_MARKER)
    assert RepositoryChunkEmbeddingService.source_text(chunk).endswith("x" * 12_100)


def test_exact_symbol_titles_identifies_code_symbols_only() -> None:
    assert RepositoryRetrievalService._exact_symbol_titles("Where is StudentLifeEnv defined?") == ["studentlifeenv"]
    assert RepositoryRetrievalService._exact_symbol_titles("How does parse_file work?") == ["parse_file"]
    assert RepositoryRetrievalService._exact_symbol_titles("How is the environment related?") == []


def test_query_embedding_failure_falls_back_to_lexical_search() -> None:
    class FailingEmbeddingProvider:
        async def embed(self, inputs, task_type=None):
            del inputs, task_type
            raise EmbeddingProviderError("provider unavailable")

    service = RepositoryRetrievalService(
        SimpleNamespace(embedding_dimensions=1536), FailingEmbeddingProvider()
    )

    assert asyncio.run(service._query_vector("authentication")) is None


class FakeRetrievalService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.args = None

    async def search(self, session, repository_id, owner_id, query, source_type, chunk_type, limit):
        del session
        if self.error:
            raise self.error
        self.args = (repository_id, owner_id, query, source_type, chunk_type, limit)
        timestamp = datetime.now(UTC)
        chunk = RepositoryChunkRead(
            id=uuid4(), repository_id=repository_id, repository_file_id=None, path="auth.py",
            chunk_type="function", source_type="source_code", title="authenticate", language="Python",
            content="def authenticate(): pass", start_line=1, end_line=1, metadata={},
            created_at=timestamp, updated_at=timestamp,
        )
        return RepositorySearchResponse(
            repository_id=repository_id, query=query, vector_search_used=True,
            results=[RepositorySearchResult(chunk=chunk, score=0.9, lexical_score=0.2, vector_score=0.95)],
        )


def test_search_endpoint_is_owner_scoped_and_passes_filters() -> None:
    service = FakeRetrievalService()
    response = asyncio.run(search_repository(
        REPOSITORY_ID, query="authentication", source_type="source_code", chunk_type="function", limit=5,
        session=object(), service=service, current_user=SimpleNamespace(id=OWNER_ID),
    ))
    assert response.results[0].chunk.path == "auth.py"
    assert service.args == (REPOSITORY_ID, OWNER_ID, "authentication", "source_code", "function", 5)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(search_repository(
            REPOSITORY_ID, query="authentication", source_type=None, chunk_type=None, limit=5,
            session=object(), service=FakeRetrievalService(RepositoryNotFoundError()),
            current_user=SimpleNamespace(id=OWNER_ID),
        ))
    assert exc.value.status_code == 404
