from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_knowledge_item import RepositoryKnowledgeItem
from app.modules.knowledge.enums import RepositoryKnowledgeSourceType
from app.modules.knowledge.schemas import (
    RepositoryKnowledgeItemListResponse,
    RepositoryKnowledgeItemRead,
)
from app.modules.parsing.results import RepositoryParseResult
from app.modules.repositories.service import RepositoryNotFoundError


@dataclass(frozen=True)
class KnowledgeItem:
    source_type: RepositoryKnowledgeSourceType
    item_type: str
    extractor: str
    data: dict
    repository_file_id: UUID | None = None
    path: str | None = None
    name: str | None = None
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class KnowledgeExtractionContext:
    repository_id: UUID
    repository_path: Path
    files: list[RepositoryFile]
    parse_result: RepositoryParseResult | None = None


@dataclass(frozen=True)
class RepositoryKnowledgeExtractionResult:
    items: list[KnowledgeItem]

    @property
    def total_items(self) -> int:
        return len(self.items)


class RepositoryKnowledgeServiceImpl:
    def __init__(self, extractors: Iterable | None = None) -> None:
        if extractors is None:
            from app.modules.knowledge.extractors.config import ConfigurationKnowledgeExtractor
            from app.modules.knowledge.extractors.documentation import DocumentationKnowledgeExtractor
            from app.modules.knowledge.extractors.schema import PrismaSchemaKnowledgeExtractor
            from app.modules.knowledge.extractors.source import SourceCodeKnowledgeExtractor

            extractors = [
                SourceCodeKnowledgeExtractor(),
                DocumentationKnowledgeExtractor(),
                PrismaSchemaKnowledgeExtractor(),
                ConfigurationKnowledgeExtractor(),
            ]
        self.extractors = list(extractors)

    def extract_repository(self, context: KnowledgeExtractionContext) -> RepositoryKnowledgeExtractionResult:
        items: list[KnowledgeItem] = []
        for extractor in self.extractors:
            items.extend(extractor.extract(context))
        return RepositoryKnowledgeExtractionResult(items=items)

    async def replace_repository_knowledge(
        self,
        session: AsyncSession,
        repository_id: UUID,
        extraction_result: RepositoryKnowledgeExtractionResult,
    ) -> None:
        await session.execute(
            delete(RepositoryKnowledgeItem).where(RepositoryKnowledgeItem.repository_id == repository_id)
        )
        session.add_all(
            [
                RepositoryKnowledgeItem(
                    repository_id=repository_id,
                    repository_file_id=item.repository_file_id,
                    path=item.path,
                    source_type=item.source_type.value,
                    item_type=item.item_type,
                    name=item.name,
                    extractor=item.extractor,
                    data=item.data,
                    extracted_at=item.extracted_at,
                )
                for item in extraction_result.items
            ]
        )

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
        await self._ensure_repository_owner(session, repository_id, owner_id)

        filters = [RepositoryKnowledgeItem.repository_id == repository_id]
        if source_type:
            filters.append(RepositoryKnowledgeItem.source_type == source_type)
        if item_type:
            filters.append(RepositoryKnowledgeItem.item_type == item_type)
        if path_prefix:
            filters.append(RepositoryKnowledgeItem.path.startswith(path_prefix))

        result = await session.execute(
            select(RepositoryKnowledgeItem)
            .where(*filters)
            .order_by(
                RepositoryKnowledgeItem.source_type.asc(),
                RepositoryKnowledgeItem.path.asc(),
                RepositoryKnowledgeItem.item_type.asc(),
                RepositoryKnowledgeItem.name.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        )
        items = result.scalars().all()
        return RepositoryKnowledgeItemListResponse(
            knowledge_items=[
                RepositoryKnowledgeItemRead.model_validate(item)
                for item in items[:page_size]
            ],
            page=page,
            page_size=page_size,
            has_next_page=len(items) > page_size,
        )

    async def _ensure_repository_owner(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> None:
        result = await session.execute(
            select(Repository.id).where(
                Repository.id == repository_id,
                Repository.owner_id == owner_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise RepositoryNotFoundError
