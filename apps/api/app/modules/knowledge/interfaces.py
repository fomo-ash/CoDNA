from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.schemas import RepositoryKnowledgeItemListResponse
from app.modules.knowledge.service import KnowledgeExtractionContext, RepositoryKnowledgeExtractionResult


class RepositoryKnowledgeExtractor(Protocol):
    name: str

    def extract(self, context: KnowledgeExtractionContext) -> list:
        ...


class RepositoryKnowledgeService(Protocol):
    def extract_repository(self, context: KnowledgeExtractionContext) -> RepositoryKnowledgeExtractionResult:
        ...

    async def replace_repository_knowledge(
        self,
        session: AsyncSession,
        repository_id: UUID,
        extraction_result: RepositoryKnowledgeExtractionResult,
    ) -> None:
        ...

    async def list_repository_knowledge_items(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
        page: int,
        page_size: int,
        source_type: str | None = None,
        item_type: str | None = None,
        path_prefix: str | None = None,
    ) -> RepositoryKnowledgeItemListResponse:
        ...
