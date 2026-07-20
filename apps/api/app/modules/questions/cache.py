from __future__ import annotations

import hashlib
import re
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_question_cache import RepositoryQuestionCache
from app.modules.questions.schemas import RepositoryAnswerCitation, RepositoryQuestionResponse


class AnswerCache(Protocol):
    async def get(self, session: AsyncSession, repository_id: UUID, owner_id: UUID, question: str) -> RepositoryQuestionResponse | None: ...

    async def save(self, session: AsyncSession, response: RepositoryQuestionResponse) -> None: ...


class DatabaseAnswerCache:
    CACHE_VERSION = "v8"

    @staticmethod
    def question_hash(question: str) -> str:
        normalized = re.sub(r"\s+", " ", question.strip().lower())
        return hashlib.sha256(f"{DatabaseAnswerCache.CACHE_VERSION}:{normalized}".encode("utf-8")).hexdigest()

    async def get(
        self, session: AsyncSession, repository_id: UUID, owner_id: UUID, question: str
    ) -> RepositoryQuestionResponse | None:
        row = await session.execute(
            select(RepositoryQuestionCache)
            .join(Repository, Repository.id == RepositoryQuestionCache.repository_id)
            .where(
                RepositoryQuestionCache.repository_id == repository_id,
                Repository.owner_id == owner_id,
                RepositoryQuestionCache.question_hash == self.question_hash(question),
                RepositoryQuestionCache.repository_indexed_at == Repository.last_indexed_at,
            )
        )
        cached = row.scalar_one_or_none()
        if cached is None:
            return None
        return RepositoryQuestionResponse(
            repository_id=repository_id,
            question=question,
            answer=cached.answer,
            citations=[RepositoryAnswerCitation.model_validate(citation) for citation in cached.citations],
            vector_search_used=cached.vector_search_used,
            cached=True,
        )

    async def save(self, session: AsyncSession, response: RepositoryQuestionResponse) -> None:
        indexed_at = await session.scalar(
            select(Repository.last_indexed_at).where(Repository.id == response.repository_id)
        )
        if indexed_at is None:
            return
        session.add(RepositoryQuestionCache(
            repository_id=response.repository_id,
            question_hash=self.question_hash(response.question),
            repository_indexed_at=indexed_at,
            answer=response.answer,
            citations=[citation.model_dump(mode="json") for citation in response.citations],
            vector_search_used=response.vector_search_used,
        ))
        await session.commit()
